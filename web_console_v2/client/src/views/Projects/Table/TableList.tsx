import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { useTranslation } from 'react-i18next'
import TableItem from './TableItem'

const Container = styled.div`
  min-width: 1160px;
`

const HeaderContainer = styled.div`
  display: flex;
  width: 100%;
  height: 34px;
  background-color: var(--gray2);
  padding: 0 16px;
`

const HeaderItemContainer = styled.div`
  font-weight: 500;
  font-size: 12px;
  line-height: 34px;
  color: #424e66;
  flex: 1;
`
interface TableConfig {
  i18nKey: string
  width: number
  jsx?: React.ReactNode
}

const TableConfigs: TableConfig[] = [
  {
    i18nKey: 'project.name',
    width: 298,
  },
  {
    i18nKey: 'project.connection_status',
    width: 149,
  },
  {
    i18nKey: 'project.workflow_number',
    width: 175,
  },
  {
    i18nKey: 'project.creator',
    width: 133,
  },
  {
    i18nKey: 'project.creat_time',
    width: 190,
  },
  {
    i18nKey: 'operation',
    width: 183,
  },
]

function Header(): ReactElement {
  return (
    <HeaderContainer>
      {TableConfigs.map((i) => (
        <HeaderItem {...i} key={i.i18nKey} width={i.width} />
      ))}
    </HeaderContainer>
  )
}

interface HeaderItemProps {
  i18nKey: string
  width: number
}

function HeaderItem({ i18nKey, width }: HeaderItemProps): ReactElement {
  const { t } = useTranslation()
  return <HeaderItemContainer style={{ flex: width }}>{t(i18nKey)}</HeaderItemContainer>
}

interface TableListProps {
  projectList: Project[]
}

function TableList({ projectList }: TableListProps): ReactElement {
  return (
    <Container>
      <Header />
      {projectList.map((item, index) => (
        <TableItem item={item} tableConfigs={TableConfigs} key={index} />
      ))}
    </Container>
  )
}

export default TableList
