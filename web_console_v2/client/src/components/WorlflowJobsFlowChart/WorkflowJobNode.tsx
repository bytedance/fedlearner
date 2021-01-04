import React, { FunctionComponent } from 'react'
import { Handle, NodeComponentProps, Position } from 'react-flow-renderer'
import styled from 'styled-components'
import configuringIcon from 'assets/icons/workflow-configuring.svg'
import completetdIcon from 'assets/icons/workflow-completed.svg'
import warningIcon from 'assets/icons/workflow-warning.svg'
import GridRow from 'components/_base/GridRow'
import { JobNodeData, JobNodeStatus } from './helpers'
import i18n from 'i18n'

const Container = styled.div``
const JobName = styled.h5`
  font-size: 16px;
  line-height: 20px;
  white-space: nowrap;
  color: var(--textColorStrong);
`
const StatusIcon = styled.img`
  display: block;
  width: 16px;
  height: 16px;
`
const JobStatusText = styled.small`
  font-size: 13px;
  color: var(--textColorSecondary);
`

const statusIcons: Record<JobNodeStatus, string> = {
  [JobNodeStatus.Pending]: '',
  [JobNodeStatus.Configuring]: configuringIcon,
  [JobNodeStatus.Completed]: completetdIcon,
  [JobNodeStatus.Unfinished]: warningIcon,
}

const statusText: Record<JobNodeStatus, string> = {
  [JobNodeStatus.Pending]: i18n.t('workflow.job_node_pending'),
  [JobNodeStatus.Configuring]: i18n.t('workflow.job_node_configuring'),
  [JobNodeStatus.Completed]: i18n.t('workflow.job_node_completed'),
  [JobNodeStatus.Unfinished]: i18n.t('workflow.job_node_unfinished'),
}

interface Props extends NodeComponentProps {
  data: JobNodeData
}

const WorkflowJobNode: FunctionComponent<Props> = ({ data, id }) => {
  const icon = statusIcons[data.status]
  const text = statusText[data.status]

  return (
    <Container>
      {data.isTarget && <Handle type="target" position={Position.Top} />}
      <JobName>{id}</JobName>
      <GridRow gap={5}>
        {icon && <StatusIcon src={icon} alt="" />}
        <JobStatusText>{text}</JobStatusText>
      </GridRow>
      {data.isSource && <Handle type="source" position={Position.Bottom} />}
    </Container>
  )
}

export default WorkflowJobNode
