import React, { ReactElement, useState, useEffect, useCallback } from 'react'
import CardPaenl from 'components/Container/CardPanel'
import Action from './Action'
import { useTranslation } from 'react-i18next'
import CardList from './Card/CardList'
import TableLish from './Table/TableList'
import { Pagination } from 'antd'

const project_list: Project[] = new Array(100)
for (let i = 0; i < project_list.length; i++) {
  project_list[i] = {
    name: 'test',
    time: 1607509226188,
  }
}

function ProjectsPage(): ReactElement {
  const { t } = useTranslation()
  const [projectList, setProjectList] = useState([] as Project[])
  const [page_size, setPageSize] = useState(10)
  const [currentPage, setCurrentPage] = useState(1)
  const [total, setTotal] = useState(100)
  const [displayType, setDisplayType] = useState(1)

  const changeHandle = useCallback(async () => {
    try {
      const ProjectList = await getProjectList(page_size, currentPage)
      setProjectList(ProjectList.project_list)
      setPageSize(ProjectList.pagination.page_size)
      setTotal(ProjectList.pagination.total)
    } catch (e) {}
  }, [page_size, currentPage])

  useEffect(() => {
    changeHandle()
  }, [changeHandle])
  return (
    <CardPaenl title={t('menu_label_project')}>
      <Action
        onDisplayTypeChange={(type: number) => {
          setDisplayType(type)
        }}
      />
      {displayType === 1 ? <CardList projectList={projectList} /> : <TableLish />}
      <Pagination size="small" total={total} showSizeChanger onChange={changeHandle} />
    </CardPaenl>
  )
}
// FIXME
function getProjectList(page_size: number | undefined, page: number): Promise<ProjectList> {
  return new Promise((res, rej) => {
    page_size = Number(page_size)
    const projectList: Project[] = project_list.slice(page_size * (page - 1), page_size * page)
    const config: PaginationConfig = {
      total: 100,
      page_size: page_size,
      page,
    }
    res({
      project_list: projectList,
      pagination: config,
    })
  })
}

export default ProjectsPage
