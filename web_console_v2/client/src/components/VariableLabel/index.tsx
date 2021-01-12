import React, { FunctionComponent } from 'react'
import { Tooltip } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'
import { VariableAccessMode } from 'typings/workflow'
import VariablePermission from 'components/VariblePermission'
import GridRow from 'components/_base/GridRow'
import styled from 'styled-components'

const LabelText = styled.span`
  font-size: 13px;
  line-height: 22px;
`

type Props = {
  label: string
  tooltip?: string
  access_mode: VariableAccessMode
}

const indicators: Record<VariableAccessMode, FunctionComponent> = {
  [VariableAccessMode.PEER_READABLE]: VariablePermission.Readable,
  [VariableAccessMode.PEER_WRITABLE]: VariablePermission.Writable,
  [VariableAccessMode.PRIVATE]: VariablePermission.Private,
  [VariableAccessMode.UNSPECIFIED]: VariablePermission.Private,
}

function VariableLabel({ label, tooltip, access_mode }: Props) {
  const PermissionIndicator = indicators[access_mode]

  if (!tooltip) {
    return (
      <GridRow gap="8">
        <PermissionIndicator />

        <LabelText>{label}</LabelText>
      </GridRow>
    )
  }

  return (
    <GridRow gap="8">
      <PermissionIndicator />

      <Tooltip title={tooltip}>
        <LabelText>
          {label}
          <QuestionCircleOutlined style={{ marginLeft: '5px' }} />
        </LabelText>
      </Tooltip>
    </GridRow>
  )
}

export default VariableLabel
