import React, { ReactElement, useState, useEffect } from 'react'
import CardPaenl from 'components/Container/CardPanel'
import Action from './Action'
import { useTranslation } from 'react-i18next'
import CardList from './Card/CardList'
import TableList from './Table/TableList'
import { Pagination } from 'antd'
import styled, { createGlobalStyle } from 'styled-components'
import { projectListQuery } from 'stores/projects'
import { useRecoilQuery } from 'hooks/recoil'
import { DisplayType } from 'typings/enum'
import { Project } from 'typings/project'

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
`

const PaginationStyle = styled(Pagination)`
  padding: 20px 0 !important;
  float: right;
`

function ProjectsPage(): ReactElement {
  const { t } = useTranslation()

  const [projectListShow, setProjectListShow] = useState([] as Project[])
  const [pageSize, setPageSize] = useState(12)
  const [currentPage, setCurrentPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [displayType, setDisplayType] = useState(DisplayType.Card)
  const { isLoading, data: projectList } = useRecoilQuery(projectListQuery)

  useEffect(() => {
    if (projectList) {
      setProjectListShow(projectList.slice((currentPage - 1) * pageSize, currentPage * pageSize))
      setTotal(projectList.length)
    }
  }, [pageSize, currentPage, projectList])

  if (isLoading) return <span>loading</span>

  return (
    <CardPaenl title={t('menu_label_project')} tip={t('project.describe')}>
      <Action
        onDisplayTypeChange={(type: number) => {
          setDisplayType(type)
        }}
      />
      {displayType === DisplayType.Card ? (
        <CardList projectList={projectListShow} />
      ) : (
        <TableList projectList={projectListShow} />
      )}
      <PaginationStyle
        pageSizeOptions={['12', '24', '36']}
        pageSize={pageSize}
        size="small"
        total={total}
        current={currentPage}
        showSizeChanger
        onChange={handleChange}
      />
      <GlobalStyle />
    </CardPaenl>
  )
  function handleChange(currentPage: number, page_size: number | undefined) {
    setCurrentPage(currentPage)
    setPageSize(Number(page_size))
  }
}

export default ProjectsPage
