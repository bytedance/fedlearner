import React, { ReactElement } from 'react'
import CardPaenl from 'components/Container/CardPanel'
import Action from 'components/Container/Projects/Action'
import { useTranslation } from 'react-i18next'
import CardList from 'components/Container/Projects/Card/CardList'
// import TableLish from 'components/Container/Projects/Table/TableList'
import { Pagination } from 'antd'

const project_list: Project[] = new Array(100)
for (let i = 0; i < project_list.length; i++) {
  project_list[i] = {
    name: i + '',
    time: Number(new Date()),
  }
}

function ProjectsPage(): ReactElement {
  const { t } = useTranslation()
  return (
    <CardPaenl title={t('menu_label_project')}>
      <Action />
      <CardList projectList={project_list} />
      <Pagination size="small" total={project_list.length} showSizeChanger />
    </CardPaenl>
  )
}

// function getProjectList() {}

export default ProjectsPage
