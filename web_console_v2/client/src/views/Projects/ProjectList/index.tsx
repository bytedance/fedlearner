import React, { ReactElement, useState, useEffect, useMemo } from 'react';
import { useQuery } from 'react-query';
import { useHistory } from 'react-router';
import { useUrlState } from 'hooks';
import { useRecoilQuery } from 'hooks/recoil';
import { useReloadProjectList } from 'hooks/project';
import { useMount } from 'react-use';
import { useRecoilState } from 'recoil';
import { appPreference } from 'stores/app';
import { projectListQuery } from 'stores/project';
import { Pagination, Spin, Grid, Button, Space, Message } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import ProjectListFilters from './ProjectListFilters';
import CardView from './CardView';
import TableView from './TableView';
import GridRow from 'components/_base/GridRow';
import NoResult from 'components/NoResult';
import TodoPopover from 'components/TodoPopover';
import { deletePendingProject, deleteProject, fetchPendingProjectList } from 'services/project';
import { DisplayType } from 'typings/component';
import { Project, ProjectListType, ProjectStateType } from 'typings/project';
import { ParticipantType } from 'typings/participant';
import { transformRegexSpecChar } from 'shared/helpers';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { PENDING_PROJECT_FILTER_MAPPER } from '../shard';

import styles from './index.module.less';
import { fetchWorkflowList } from 'services/workflow';
import Modal from 'components/Modal';

const { Row } = Grid;

function ProjectList(): ReactElement {
  const history = useHistory();

  const [projectListShow, setProjectListShow] = useState([] as Project[]);

  const [urlState, setUrlState] = useUrlState({
    pageSize: 12,
    page: 1,
    keyword: '',
    participant_type: [],
    project_list_type: ProjectListType.COMPLETE,
  });

  const [total, setTotal] = useState(0);

  const [preference, setPreference] = useRecoilState(appPreference);

  const reloadList = useReloadProjectList();
  const { isLoading, data: projectList } = useRecoilQuery(projectListQuery);
  const pendingProjectListQuery = useQuery(
    ['fetchPendingProjectList'],
    () =>
      fetchPendingProjectList({
        filter: filterExpressionGenerator(
          {
            state: [ProjectStateType.ACCEPTED, ProjectStateType.FAILED],
          },
          PENDING_PROJECT_FILTER_MAPPER,
        ),
        page: 1,
        page_size: 0,
      }),
    {
      retry: 2,
    },
  );
  const { pendingProjectListShow, pendingProjectListTotal } = useMemo(() => {
    const pendingProjectList = pendingProjectListQuery?.data?.data;
    const regx = new RegExp(`^.*${transformRegexSpecChar(urlState.keyword)}.*$`);
    const filedPendingProjectList = pendingProjectList?.filter((item) => {
      return (
        (regx.test(item.name) &&
          (!urlState.participant_type.length ||
            (!item.participant_type &&
              urlState.participant_type.includes(ParticipantType.PLATFORM)) ||
            urlState.participant_type.includes(item.participant_type))) ||
        item.state !== ProjectStateType.PENDING
      );
    });
    return {
      pendingProjectListShow: filedPendingProjectList?.slice(
        (urlState.page - 1) * urlState.pageSize,
        urlState.page * urlState.pageSize,
      ),
      pendingProjectListTotal: filedPendingProjectList?.length ?? 0,
    };
  }, [pendingProjectListQuery, urlState]);

  const { nowProjectListShow, listTotal } = useMemo(() => {
    if (urlState.project_list_type === ProjectListType.PENDING) {
      return { nowProjectListShow: pendingProjectListShow, listTotal: pendingProjectListTotal };
    }
    return {
      nowProjectListShow: projectListShow,
      listTotal: total,
    };
  }, [pendingProjectListShow, projectListShow, urlState, total, pendingProjectListTotal]);

  const isEmpty = listTotal === 0;

  useMount(() => {
    if (!isLoading || projectList) {
      // If the projectListQuery is not fetching when enter the page
      // means project list data on store may has a chance tobe stale
      // so what we do is force to reload the list once entering
      reloadList();
    }
  });

  useEffect(() => {
    if (projectList) {
      const regx = new RegExp(`^.*${transformRegexSpecChar(urlState.keyword)}.*$`);
      const filtedProjectList = projectList.filter((item) => {
        return (
          regx.test(item.name) &&
          (!urlState.participant_type.length ||
            (!item.participant_type &&
              urlState.participant_type.includes(ParticipantType.PLATFORM)) ||
            urlState.participant_type.includes(item.participant_type))
        );
      });
      setProjectListShow(
        filtedProjectList.slice(
          (urlState.page - 1) * urlState.pageSize,
          urlState.page * urlState.pageSize,
        ),
      );
      setTotal(filtedProjectList.length);
    }
  }, [projectList, urlState]);

  return (
    <div className={styles.pagination_container}>
      <GridRow justify="space-between">
        <div>
          <h2>Hi，欢迎来到隐私计算平台</h2>
          <p>打破数据孤岛，实现数据跨域共享开放，安全激活数据使用价值</p>
        </div>
        <div>
          <Space>
            <Button
              className={'custom-operation-button'}
              type="primary"
              onClick={() => {
                history.push('/projects/create');
              }}
              icon={<IconPlus />}
            >
              创建工作区
            </Button>
            <TodoPopover.ProjectNotice />
          </Space>
        </div>
      </GridRow>
      <Spin loading={isLoading} className={styles.spin_container}>
        <ProjectListFilters
          onDisplayTypeChange={(type: DisplayType) => {
            setPreference({
              ...preference,
              projectsDisplay: type,
            });
          }}
          onProjectListTypeChange={(type: ProjectListType) => {
            setUrlState((prevState) => ({
              ...prevState,
              project_list_type: type,
              page: 1,
            }));
          }}
          onSearch={onSearch}
          defaultSearchText={urlState.keyword}
          projectListType={urlState.project_list_type}
        />
        <section className={styles.list_container}>
          {isEmpty && preference.projectsDisplay === DisplayType.Card ? (
            <NoResult text={'暂无工作区'} to="/projects/create" />
          ) : preference.projectsDisplay === DisplayType.Card ? (
            <CardView
              list={nowProjectListShow ?? []}
              onViewDetail={viewDetail}
              projectListType={urlState.project_list_type}
              onDeleteProject={handleDelete}
            />
          ) : (
            <TableView
              list={nowProjectListShow ?? []}
              onViewDetail={viewDetail}
              onParticipantTypeChange={onParticipantTypeChange}
              participantType={urlState.participant_type}
              projectLisType={urlState.project_list_type}
              onDeleteProject={handleDelete}
            />
          )}
        </section>

        <Row justify="end">
          {!isEmpty && (
            <Pagination
              className={styles.pagination_container}
              pageSize={Number(urlState.pageSize)}
              sizeOptions={[12, 24]}
              total={listTotal}
              showTotal={true}
              current={Number(urlState.page)}
              sizeCanChange
              onChange={onPageChange}
            />
          )}
        </Row>
      </Spin>
    </div>
  );

  function onPageChange(page: number, pageSize: number | undefined) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }
  function viewDetail(project: Project) {
    history.push(`/projects/${urlState.project_list_type}/detail/${project.id}`);
  }
  function onSearch(value: string) {
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
      keyword: value,
    }));
  }
  function onParticipantTypeChange(value: string[]) {
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
      participant_type: value,
    }));
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
              pendingProjectListQuery.refetch();
            } catch (error: any) {
              Message.error(error.message);
            }
          } else {
            try {
              await deleteProject(projectId);
              Message.success('删除工作区成功');
              reloadList();
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
}

export default ProjectList;
