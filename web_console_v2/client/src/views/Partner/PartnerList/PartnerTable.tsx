import React, { FC, useMemo, useState } from 'react';
import { useHistory } from 'react-router-dom';
import { useMount } from 'react-use';

import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import { useReloadParticipantList } from 'hooks/participant';
import { useUrlState } from 'hooks';

import { participantListQuery } from 'stores/participant';
import { deleteParticipant } from 'services/participant';
import { transformRegexSpecChar } from 'shared/helpers';
import { formatTimestamp } from 'shared/date';
import { CONSTANTS } from 'shared/constants';

import { Button, Input, Message, Table } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import { Plus } from 'components/IconPark';
import Modal from 'components/Modal';
import StateIndicator from 'components/StateIndicator';
import PaticipantConnectionStatus, {
  globalParticipantIdToConnectionStateMap,
} from './ConnectionStatus';
import { ActionItem, VersionItem } from './TableItem';

import { FedRoles } from 'typings/auth';
import { Participant, ParticipantType } from 'typings/participant';

import styles from './PartnerTable.module.less';

export const getParticipant_columns = (showNumOfWorkspace: boolean) => {
  const columns = [
    {
      title: '企业名称',
      dataIndex: 'name',
      ellipsis: true,
      sorter: (a: Participant, b: Participant) => a.name.localeCompare(b.name),
    },
    {
      title: '类型',
      dataIndex: 'type',
      filters: [
        {
          text: '轻量级',
          value: ParticipantType.LIGHT_CLIENT,
        },
        {
          text: '标准',
          value: ParticipantType.PLATFORM,
        },
      ],
      onFilter: (value: any, record: Participant) => {
        if (value === ParticipantType.LIGHT_CLIENT) {
          return record.type === ParticipantType.LIGHT_CLIENT;
        }
        if (value === ParticipantType.PLATFORM) {
          return record.type === ParticipantType.PLATFORM || record.type == null;
        }
        return false;
      },
      render: (value: ParticipantType) => (
        <StateIndicator.LigthClientType isLightClient={value === ParticipantType.LIGHT_CLIENT} />
      ),
    },
    {
      title: '状态',
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
        // Keep default order
        return 1;
      },
      render: (_: any, record: Participant) => {
        const isLightClient = record.type === ParticipantType.LIGHT_CLIENT;

        if (isLightClient) {
          return CONSTANTS.EMPTY_PLACEHOLDER;
        }

        return <PaticipantConnectionStatus id={record.id} isNeedTip={true} isNeedReCheck={true} />;
      },
    },
    {
      title: '泛域名',
      dataIndex: 'domain_name',
      sorter: (a: Participant, b: Participant) => a.domain_name.localeCompare(b.domain_name),
    },
    {
      title: '主机号',
      dataIndex: 'host',
    },
    {
      title: '端口号',
      dataIndex: 'port',
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
        return value || CONSTANTS.EMPTY_PLACEHOLDER;
      },
    },
    {
      title: '最近活跃时间',
      dataIndex: 'last_connected_at',
      render: (value: any) => {
        return value ? formatTimestamp(value) : CONSTANTS.EMPTY_PLACEHOLDER;
      },
      sorter: (a: Participant, b: Participant) =>
        (a.last_connected_at || 0) - (b.last_connected_at || 0),
    },
  ];
  showNumOfWorkspace &&
    columns.push({
      title: '已关联的工作区数量',
      dataIndex: 'num_project',
      render: (value: any) => {
        return value || 0;
      },
    });
  return columns;
};

const PartnerTable: FC = () => {
  const history = useHistory();
  const userInfo = useRecoilQuery(userInfoQuery);
  const reloadParticipants = useReloadParticipantList();
  const { isLoading, data: participantList } = useRecoilQuery(participantListQuery);
  const reloadList = useReloadParticipantList();
  const [isDeleting, setIsDeleting] = useState(false);

  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 20,
    keyword: '',
  });

  useMount(() => {
    if (!isLoading || participantList) {
      reloadList();
    }
  });

  const showList = useMemo(() => {
    if (participantList && urlState.keyword) {
      const regx = new RegExp(`^.*${transformRegexSpecChar(urlState.keyword)}.*$`);
      return participantList.filter((item: Participant) => regx.test(item.name));
    }
    return participantList || [];
  }, [participantList, urlState.keyword]);

  const isAdmin = useMemo(() => {
    if (userInfo.data) {
      const _isAdmin = userInfo.data.role === FedRoles.Admin;
      return _isAdmin;
    }
    return false;
  }, [userInfo.data]);

  const columns = getParticipant_columns(true);

  isAdmin &&
    columns.push({
      title: '操作',
      dataIndex: 'action',
      render: (_: any, record: any) => {
        return (
          <ActionItem
            data={record}
            onDelete={() => {
              Modal.delete({
                title: '确认要删除合作伙伴？',
                content: '删除后，该合作伙伴将退出当前所有运行中的工作流',
                onOk() {
                  handleDelete(record.id);
                },
              });
            }}
          />
        );
      },
    });

  return (
    <>
      <GridRow justify={isAdmin ? 'space-between' : 'end'}>
        {isAdmin && (
          <Button icon={<Plus />} type="primary" onClick={() => history.push('/partners/create')}>
            添加合作伙伴
          </Button>
        )}
        <Input.Search
          allowClear
          onSearch={onSearch}
          onClear={() => onSearch('')}
          placeholder="输入合作伙伴名称搜索"
          defaultValue={urlState.keyword}
        />
      </GridRow>
      <Table<Participant>
        className={`custom-table custom-table-left-side-filter ${styles.table_container}`}
        rowKey="id"
        data={showList}
        columns={columns}
        pagination={{
          pageSize: Number(urlState.pageSize),
          current: Number(urlState.page),
          onChange: onPageChange,
        }}
        loading={isLoading || isDeleting}
      />
    </>
  );

  function onSearch(value: string) {
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
      keyword: value,
    }));
  }
  function onPageChange(page: number, pageSize: number | undefined) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }

  async function handleDelete(id: ID) {
    try {
      setIsDeleting(true);
      await deleteParticipant(id);
      setIsDeleting(false);
      Message.success('删除成功');
      reloadParticipants();
    } catch (error: any) {
      setIsDeleting(false);
      Message.error(error.message);
    }
  }
};

export default PartnerTable;
