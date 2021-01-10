import React, { ReactElement, useState } from 'react'
import styled, { CSSProperties } from 'styled-components'
import { Divider } from 'antd'
import { Project } from 'typings/project'
import ProjectConnectionStatus from '../ConnectionStatus'
import CreateTime from '../CreateTime'
import ProjectName from '../ProjectName'
import ProjectAction from '../ProjectAction'
import Detail from '../Detail'
import { useHistory } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const Container = styled.div`
  display: flex;
  width: 100%;
  padding: 0 16px;
`

const ContainerItem = styled.div`
  flex: 1;
  overflow: hidden;
  .project-connection-status {
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
  cursor: pointer;
  &:not(:first-child) {
    margin-left: 16px;
  }
`

interface TableConfig {
  i18nKey: string
  width: number
}
interface TableItemProps {
  tableConfigs: TableConfig[]
  item: Project
}

interface DescribeProps {
  text: string
  style: CSSProperties
}

function Describe({ text, style }: DescribeProps): ReactElement {
  return <DescribeContainer style={style}>{text}</DescribeContainer>
}

function Action({ project }: { project: Project }): ReactElement {
  const [isDrawerVisible, setIsDrawerVisible] = useState(false)
  const history = useHistory()
  const { t } = useTranslation()
  return (
    <ActionContainer>
      <ActionItemContainer>{t('project.check_connection')}</ActionItemContainer>
      <ActionItemContainer>{t('project.create_work_flow')}</ActionItemContainer>
      <ActionItemContainer>
        <ProjectAction
          style={{ marginTop: '13px' }}
          onEdit={() => {
            history.push({
              pathname: '/edit-project',
              state: {
                project,
              },
            })
          }}
          onDetail={() => setIsDrawerVisible(true)}
        />
      </ActionItemContainer>
      <Detail
        title={project.name}
        onClose={() => setIsDrawerVisible(false)}
        visible={isDrawerVisible}
        project={project}
      />
    </ActionContainer>
  )
}

const getCellContent = function (i18nKey: string, project: Project): ReactElement {
  switch (i18nKey) {
    case 'project.name':
      return (
        <ProjectName
          text={project.name}
          style={{ color: '#286AF4', lineHeight: '50px', fontSize: '13px', marginLeft: '0' }}
        />
      )
    case 'project.connection_status':
      return <ProjectConnectionStatus connectionStatus={1} />
    case 'project.workflow_number':
      return (
        <Describe text={'12'} style={{ lineHeight: '50px', color: '#1A2233', fontSize: '13px' }} />
      )
    case 'project.creator':
      // fixme
      return (
        <Describe
          text={'陈盛明'}
          style={{ lineHeight: '50px', color: '#1A2233', fontSize: '13px' }}
        />
      )
    case 'project.creat_time':
      return (
        <CreateTime time={project.created_at} style={{ lineHeight: '50px', color: '#1A2233' }} />
      )
    case 'operation':
      return <Action project={project} />
    default:
      return null as never
  }
}

function TableItem({ tableConfigs, item }: TableItemProps): ReactElement {
  return (
    <>
      <Container>
        {tableConfigs.map((i) => (
          <ContainerItem style={{ flex: i.width }} key={i.i18nKey}>
            {getCellContent(i.i18nKey, item)}
          </ContainerItem>
        ))}
      </Container>
      <Divider style={{ margin: 0 }} />
    </>
  )
}

export default TableItem
