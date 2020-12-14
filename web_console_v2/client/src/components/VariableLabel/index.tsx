import React from 'react'
import { Tooltip } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'

type Props = {
  label: string
  tooltip?: string
}

function VariableLabel({ label, tooltip }: Props) {
  if (!tooltip) {
    return <span>{label}</span>
  }

  return (
    <Tooltip title={tooltip}>
      <span>
        {label}
        <QuestionCircleOutlined style={{ margin: '0 3px' }} />
      </span>
    </Tooltip>
  )
}

export default VariableLabel
