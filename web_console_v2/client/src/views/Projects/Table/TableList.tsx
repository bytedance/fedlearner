import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Divider } from 'antd'
import { useTranslation } from 'react-i18next'
import TableItem from './TableItem'
import ConnectStatus from '../ConnectStatus'

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
  i18Key: string
  width: number
  jsx?: React.ReactNode
}

const TableConfigs: TableConfig[] = [
  {
    i18Key: 'project_name',
    width: 298,
  },
  {
    i18Key: 'project_connect_status',
    width: 149,
  },
  {
    i18Key: 'project_workflow_number',
    width: 175,
  },
  {
    i18Key: 'project_creator',
    width: 133,
  },
  {
    i18Key: 'project_creat_time',
    width: 190,
  },
  {
    i18Key: 'operation',
    width: 183,
  },
]

function Header(): ReactElement {
  return (
    <HeaderContainer>
      {TableConfigs.map((i) => (
        <HeaderItem {...i} key={i.i18Key} width={i.width} />
      ))}
    </HeaderContainer>
  )
}

interface HeaderItemProps {
  i18Key: string
  width: number
}

function HeaderItem({ i18Key, width }: HeaderItemProps): ReactElement {
  const { t } = useTranslation()
  return <HeaderItemContainer style={{ flex: width }}>{t(i18Key)}</HeaderItemContainer>
}

function TableList(): ReactElement {
  return (
    <Container>
      <Header />
      {new Array(10).fill(0).map((i) => (
        <TableItem tableConfigs={TableConfigs} key={i} />
      ))}
    </Container>
  )
}

export default TableList
