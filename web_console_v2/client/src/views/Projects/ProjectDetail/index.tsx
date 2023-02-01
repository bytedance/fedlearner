import React, { FC, useState, useMemo } from 'react';
import { useParams, useHistory } from 'react-router';
import { useQuery } from 'react-query';
import { useGetCurrentPureDomainName } from 'hooks';
import { useRecoilQuery } from 'hooks/recoil';
import {
  deletePendingProject,
  deleteProject,
  fetchPendingProjectList,
  getProjectDetailById,
} from 'services/project';
import { fetchWorkflowList } from 'services/workflow';
import { Message, Spin, Table, Tabs, Tag } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import DetailHeader from './DetailHeader';
import BackButton from 'components/BackButton';
import { VersionItem } from 'views/Partner/PartnerList/TableItem';
import { getWorkflowTableColumns } from 'views/Workflows/WorkflowList/List';
import PaticipantConnectionStatus, {
  globalParticipantIdToConnectionStateMap,
} from 'views/Partner/PartnerList/ConnectionStatus';
import { resetParticipantsInfo, PARTICIPANT_STATE_MAPPER } from '../shard';
import { formatTimestamp } from 'shared/date';
import { participantListQuery } from 'stores/participant';
import { ProjectListType, ProjectStateType } from 'typings/project';
import { ParticipantType, Participant } from 'typings/participant';

import styles from './index.module.less';
import Modal from 'components/Modal';

const ProjectDetail: FC = () => {
  const history = useHistory();
  const myPureDomainName = useGetCurrentPureDomainName();
  const { id, projectListType } = useParams<{
    id: string;
    projectListType: ProjectListType;
  }>();

  const [activeKey, setActiveKey] = useState('participant');
  const { data, isLoading } = useQuery(
    ['getProjectDetail', id, projectListType],
    () => getProjectDetailById(id),
    {
      enabled: Boolean(id) && projectListType === ProjectListType.COMPLETE,
      cacheTime: 1,
      refetchOnWindowFocus: false,
    },
  );
  const project = data?.data;

  const { data: pendingProjectList, isLoading: pendingProjectListLoading } = useQuery(
    ['fetchPendingProjectList', projectListType],
    () => fetchPendingProjectList({ page: 1, page_size: 0 }),
    { enabled: Boolean(id) && projectListType === ProjectListType.PENDING },
  );

  const workflowsQuery = useQuery(['fetchWorkflowList', id], () =>
    fetchWorkflowList({ project: id }),
  );

  const { isLoading: participantListLoading, data: participantList } = useRecoilQuery(
    participantListQuery,
  );

  const pendingProjectDetail = useMemo(() => {
    return pendingProjectList?.data.find((item) => item.id.toString() === id);
  }, [pendingProjectList, id]);

  const completeParticipantList = useMemo(() => {
    const participantListFromMap = resetParticipantsInfo(
      project?.participants_info?.participants_map ??
        pendingProjectDetail?.participants_info?.participants_map ??
        {},
      participantList ?? [],
      myPureDomainName,
    );
    return participantListFromMap.length ? participantListFromMap : project?.participants;
  }, [project, participantList, pendingProjectDetail, myPureDomainName]);

  const columns = [
    {
      title: '合作伙伴名称',
      dataIndex: 'name',
      width: 160,
      render: (value: any, record: any) =>
        record.pure_domain_name === myPureDomainName ? (
          <div className={styles.participant_name_container}>
            <span className={styles.participant_name_content}>{value}</span>
            <Tag>我方</Tag>
          </div>
        ) : (
          <span>{value}</span>
        ),
      sorter: (a: Participant, b: Participant) => a.name.localeCompare(b.name),
    },
    {
      title: '受邀状态',
      dataIndex: 'state',
      render: (val: ProjectStateType) => {
        const { color, value } = PARTICIPANT_STATE_MAPPER?.[val ?? ProjectStateType.ACCEPTED];
        return <Tag color={color}>{value}</Tag>;
      },
    },
    {
      title: '连接状态',
      dataIndex: 'status',
      width: 150,
      sorter: (a: Participant, b: Participant) => {
        if (
          globalParticipantIdToConnectionStateMap[b.id] &&
          globalParticipantIdToConnectionStateMap[a.id]
        ) {
          return globalParticipantIdToConnectionStateMap[b.id].localeCompare(
            globalParticipantIdToConnectionStateMap[a.id],
          );
        }
        return 1;
      },
      render: (_: any, record: Participant) => {
        const isLightClient = record.type === ParticipantType.LIGHT_CLIENT;
        const isMy = myPureDomainName === record.pure_domain_name;

        if (isLightClient || isMy) {
          return '-';
        }

        return <PaticipantConnectionStatus id={record.id} isNeedTip={true} isNeedReCheck={true} />;
      },
    },
    {
      title: '泛域名',
      dataIndex: 'domain_name',
      sorter: (a: Participant, b: Participant) =>
        a.domain_name ?? ''.localeCompare(b.domain_name ?? ''),
      render: (value: any) => value || '-',
    },
    {
      title: '主机号',
      dataIndex: 'host',
      render: (value: any) => value || '-',
    },
    {
      title: '端口号',
      dataIndex: 'port',
      render: (value: any) => value || '-',
    },
    {
      title: '版本号',
      dataIndex: 'version',
      render: (_: any, record: Participant) => {
        return <VersionItem partnerId={record.id} />;
      },
    },
    {
      title: '合作伙伴描述',
      dataIndex: 'comment',
      ellipsis: true,
      render: (value: any) => {
        return value || '-';
      },
    },
    {
      title: '最近活跃时间',
      dataIndex: 'last_connected_at',
      render: (value: any) => {
        return value ? formatTimestamp(value) : '-';
      },
      sorter: (a: Participant, b: Participant) =>
        (a.last_connected_at || 0) - (b.last_connected_at || 0),
    },
  ];
  return (
    <SharedPageLayout title={<BackButton onClick={() => history.goBack()}>工作区管理</BackButton>}>
      <Spin loading={isLoading || pendingProjectListLoading || participantListLoading}>
        <DetailHeader
          project={projectListType === ProjectListType.COMPLETE ? project! : pendingProjectDetail!}
          projectListType={projectListType}
          onDeleteProject={handleDelete}
        />
        <Tabs onChange={onTabChange} activeTab={activeKey}>
          <Tabs.TabPane title="合作伙伴" key="participant">
            <Table
              className="custom-table"
              columns={columns}
              data={completeParticipantList}
              rowKey="pure_domain_name"
            />
          </Tabs.TabPane>
          {projectListType === ProjectListType.COMPLETE && (
            <Tabs.TabPane title="工作流任务" key="workflow">
              <Table
                className="custom-table"
                loading={isLoading && workflowsQuery.isLoading}
                data={workflowsQuery.data?.data || []}
                columns={getWorkflowTableColumns({ withoutActions: true, withoutFavour: true })}
                rowKey="id"
              />
            </Tabs.TabPane>
          )}
        </Tabs>
      </Spin>
    </SharedPageLayout>
  );
  function onTabChange(val: string) {
    setActiveKey(val);
  }
  async function handleDelete(projectId: ID, projectListType: ProjectListType) {
    if (!projectId) {
      return;
    }
    try {
      const { data: workflowList } = await fetchWorkflowList({
        project: projectId,
        states: ['running'],
        page: 1,
        pageSize: 1,
      });
      if (Boolean(workflowList.length)) {
        Message.info('有正在运行的任务，请终止任务后再删除');
        return;
      }
      Modal.delete({
        title: '确认删除工作区？',
        content: '删除工作区将清空我方全部资源，请谨慎操作',
        async onOk() {
          if (projectListType === ProjectListType.PENDING) {
            try {
              await deletePendingProject(projectId);
              Message.success('删除工作区成功');
              history.push('/projects?project_list_type=pending');
            } catch (error: any) {
              Message.error(error.message);
            }
          } else {
            try {
              await deleteProject(projectId);
              Message.success('删除工作区成功');
              history.push('/projects?project_list_type=complete');
            } catch (error: any) {
              Message.error(error.message);
            }
          }
        },
      });
    } catch (error: any) {
      return error.message;
    }
  }
};

export default ProjectDetail;
