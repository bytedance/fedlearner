import React, { FC } from 'react';
import { Tooltip } from '@arco-design/web-react';
import { QuestionCircle } from 'components/IconPark';
import { VariableAccessMode } from 'typings/variable';
import VariablePermission from 'components/VariblePermission';
import GridRow from 'components/_base/GridRow';
import styled from './index.module.less';

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
        <span className={styled.label_text}>{label}</span>
      </GridRow>
    );
  }

  return (
    <GridRow gap="8" role="label">
      <PermissionIndicator />

      <Tooltip content={tooltip}>
        <span className={styled.label_text}>
          {label}
          <QuestionCircle style={{ marginLeft: '5px' }} />
        </span>
      </Tooltip>
    </GridRow>
  );
};

export default VariableLabel;
