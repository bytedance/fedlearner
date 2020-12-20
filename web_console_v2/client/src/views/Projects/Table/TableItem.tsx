import React, { ReactElement } from 'react'
import styled, { CSSProperties } from 'styled-components'
import { Divider } from 'antd'
import { useTranslation } from 'react-i18next'
import ConnectStatus from '../ConnectStatus'
import CreateTime from '../CreateTime'
import ProjectName from '../ProjectName'
import ProjectAction from '../ProjectAction'

const Container = styled.div`
  display: flex;
  width: 100%;
  padding: 0 16px;
`

const ContainerItem = styled.div`
  flex: 1;
  overflow: hidden;
  .project-connect-status {
    line-height: 50px;
  }
`

const DescribeContainer = styled.div``

const ActionContainer = styled.div`
  display: flex;
  line-height: 50px;
  color: var(--primaryColor);
`

const ActionItemContainer = styled.div`
  &:not(:first-child) {
    margin-left: 16px;
  }
`

interface TableConfig {
  i18Key: string
  width: number
}
interface TableItemProps {
  tableConfigs: TableConfig[]
}

interface DescribeProps {
  text: string
  style: CSSProperties
}

type getJSXType = (i18Key: string) => React.ReactNode

function Describe({ text, style }: DescribeProps): ReactElement {
  return <DescribeContainer style={style}>{text}</DescribeContainer>
}

function Action(): ReactElement {
  return (
    <ActionContainer>
      <ActionItemContainer>检查链接</ActionItemContainer>
      <ActionItemContainer>创建任务流</ActionItemContainer>
      <ActionItemContainer>
        <ProjectAction style={{ marginTop: '13px' }} />
      </ActionItemContainer>
    </ActionContainer>
  )
}

const getJSX: getJSXType = function (i18Key) {
  switch (i18Key) {
    case 'project_name':
      return (
        <ProjectName
          text={'卡卡的过来asdfasdfa fasdf 看adsfasdfas'}
          style={{ color: '#286AF4', lineHeight: '50px', fontSize: '13px', marginLeft: '0' }}
        />
      )
    case 'project_connect_status':
      return <ConnectStatus connectStatus={1} />
    case 'project_workflow_number':
      return (
        <Describe text={'12'} style={{ lineHeight: '50px', color: '#1A2233', fontSize: '13px' }} />
      )
    case 'project_creator':
      return (
        <Describe
          text={'陈盛明'}
          style={{ lineHeight: '50px', color: '#1A2233', fontSize: '13px' }}
        />
      )
    case 'project_creat_time':
      return <CreateTime time={1607509226188} style={{ lineHeight: '50px', color: '#1A2233' }} />
    case 'operation':
      return <Action />
    default:
      return null as never
  }
}

function TableItem({ tableConfigs }: TableItemProps): ReactElement {
  return (
    <>
      <Container>
        {tableConfigs.map((i) => (
          <ContainerItem style={{ flex: i.width }}>{getJSX(i.i18Key)}</ContainerItem>
        ))}
      </Container>
      <Divider style={{ margin: 0 }} />
    </>
  )
}

export default TableItem
