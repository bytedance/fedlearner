import React, { ReactElement, useState, useEffect } from 'react';
import ProjectListFilters from './ProjectListFilters';
import { useTranslation } from 'react-i18next';
import CardView from './CardView';
import TableView from './TableView';
import { Pagination, Spin, Row } from 'antd';
import styled, { createGlobalStyle } from 'styled-components';
import { projectListQuery } from 'stores/project';
import { useRecoilQuery } from 'hooks/recoil';
import { DisplayType } from 'typings/component';
import { Project } from 'typings/project';
import SharedPageLayout from 'components/SharedPageLayout';
import NoResult from 'components/NoResult';
import ProjectDetailDrawer from '../ProjectDetailDrawer';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { useMount } from 'react-use';
import { useReloadProjectList } from 'hooks/project';

const GlobalStyle = createGlobalStyle`
.project-actions {
  width: 72px;
  border: 1px solid #e5e6e8;
  box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  overflow: hidden;
  padding: 0;

  .ant-popover-content {
    .ant-popover-arrow {
      display: none !important;
    }
    .ant-popover-inner {
      border-radius: 0;
      .ant-popover-inner-content {
        padding: 0;
      }
    }
  }
}
`;
const StyledPagination = styled(Pagination)`
  margin-top: 20px;
`;
const ListContainer = styled.section`
  display: flex;
  flex: 1;
  align-items: flex-start;
`;

function ProjectList(): ReactElement {
  const { t } = useTranslation();

  const [projectListShow, setProjectListShow] = useState([] as Project[]);
  const [pageSize, setPageSize] = useState(12);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [project, setCurrentProject] = useState<Project>();
  const [displayType, setDisplayType] = useState(
    store.get(LOCAL_STORAGE_KEYS.projects_display) || DisplayType.Card,
  );

  const reloadList = useReloadProjectList();
  const { isLoading, data: projectList } = useRecoilQuery(projectListQuery);

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
      setProjectListShow(projectList.slice((currentPage - 1) * pageSize, currentPage * pageSize));
      setTotal(projectList.length);
    }
  }, [pageSize, currentPage, projectList]);

  const isEmpty = projectListShow.length === 0;

  return (
    <Spin spinning={isLoading}>
      <GlobalStyle />

      <SharedPageLayout title={t('menu.label_project')} tip={t('project.describe')}>
        <ProjectListFilters
          onDisplayTypeChange={(type: number) => {
            store.set(LOCAL_STORAGE_KEYS.projects_display, type);
            setDisplayType(type);
          }}
        />
        <ListContainer>
          {isEmpty ? (
            <NoResult text={t('project.no_result')} to="/projects/create" />
          ) : displayType === DisplayType.Card ? (
            <CardView list={projectListShow} onViewDetail={viewDetail} />
          ) : (
            <TableView list={projectListShow} onViewDetail={viewDetail} />
          )}
        </ListContainer>

        <ProjectDetailDrawer
          project={project}
          onClose={() => setDrawerVisible(false)}
          visible={drawerVisible}
        />

        <Row justify="end">
          {!isEmpty && (
            <StyledPagination
              pageSizeOptions={['12', '24']}
              pageSize={pageSize}
              total={total}
              current={currentPage}
              showSizeChanger
              onChange={onPageChange}
            />
          )}
        </Row>
      </SharedPageLayout>
    </Spin>
  );

  function onPageChange(currentPage: number, page_size: number | undefined) {
    setCurrentPage(currentPage);
    setPageSize(Number(page_size));
  }
  function viewDetail(project: Project) {
    setCurrentProject(project);
    setDrawerVisible(true);
  }
}

export default ProjectList;
