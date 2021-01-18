import React, { ReactElement, useState, useEffect } from 'react';
import ProjectListFilters from './ProjectListFilters';
import { useTranslation } from 'react-i18next';
import CardView from './CardView';
import TableView from './TableView';
import { Pagination, Spin, Row } from 'antd';
import styled, { createGlobalStyle } from 'styled-components';
import { projectListQuery } from 'stores/projects';
import { useRecoilQuery } from 'hooks/recoil';
import { DisplayType } from 'typings/component';
import { Project } from 'typings/project';
import ListPageLayout from 'components/ListPageLayout';

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
  flex: 1;
`;

function ProjectList(): ReactElement {
  const { t } = useTranslation();

  const [projectListShow, setProjectListShow] = useState([] as Project[]);
  const [pageSize, setPageSize] = useState(12);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [displayType, setDisplayType] = useState(DisplayType.Card);
  const { isLoading, data: projectList } = useRecoilQuery(projectListQuery);

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

      <ListPageLayout title={t('menu.label_project')} tip={t('project.describe')}>
        <ProjectListFilters
          onDisplayTypeChange={(type: number) => {
            setDisplayType(type);
          }}
        />
        <ListContainer>
          {displayType === DisplayType.Card ? (
            <CardView projectList={projectListShow} />
          ) : (
            <TableView projectList={projectListShow} />
          )}
        </ListContainer>

        <Row justify="end">
          <StyledPagination
            pageSizeOptions={['12', '24']}
            pageSize={pageSize}
            total={total}
            current={currentPage}
            showSizeChanger
            onChange={handleChange}
          />
        </Row>
      </ListPageLayout>
    </Spin>
  );
  function handleChange(currentPage: number, page_size: number | undefined) {
    setCurrentPage(currentPage);
    setPageSize(Number(page_size));
  }
}

export default ProjectList;
