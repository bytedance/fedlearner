import React, { FC } from 'react';
import { Tooltip } from 'antd';
import { QuestionCircle } from 'components/IconPark';
import { VariableAccessMode } from 'typings/variable';
import VariablePermission from 'components/VariblePermission';
import GridRow from 'components/_base/GridRow';
import styled from 'styled-components';

const LabelText = styled.span`
  font-size: 13px;
  line-height: 22px;
`;

type Props = {
  label: string;
  tooltip?: string;
  accessMode: VariableAccessMode;
};

export const indicators: Record<VariableAccessMode, any> = {
  [VariableAccessMode.PEER_READABLE]: VariablePermission.Readable,
  [VariableAccessMode.PEER_WRITABLE]: VariablePermission.Writable,
  [VariableAccessMode.PRIVATE]: VariablePermission.Private,
  [VariableAccessMode.UNSPECIFIED]: VariablePermission.Private,
};

const VariableLabel: FC<Props> = ({ label, tooltip, accessMode }) => {
  const PermissionIndicator = indicators[accessMode];

  if (!Boolean(tooltip)) {
    return (
      <GridRow gap="8" role="label">
        <PermissionIndicator />

        <LabelText>{label}</LabelText>
      </GridRow>
    );
  }

  return (
    <GridRow gap="8" role="label">
      <PermissionIndicator />

      <Tooltip title={tooltip}>
        <LabelText>
          {label}
          <QuestionCircle style={{ marginLeft: '5px' }} />
        </LabelText>
      </Tooltip>
    </GridRow>
  );
};

export default VariableLabel;
