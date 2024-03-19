/* istanbul ignore file */

import React, { FC } from 'react';
import { Tooltip } from '@arco-design/web-react';
import { QuestionCircle } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import styled from 'styled-components';

const LabelText = styled.span`
  font-size: 13px;
  line-height: 22px;
`;

type Props = {
  label: string;
  tooltip?: string;
  className?: string;
};

const FormLabel: FC<Props> = ({ label, tooltip, className }) => {
  if (!tooltip) {
    return <LabelText>{label}</LabelText>;
  }

  return (
    <GridRow gap="8" role="label" className={className}>
      <Tooltip content={tooltip}>
        <LabelText>
          {label}
          <QuestionCircle style={{ marginLeft: '5px' }} />
        </LabelText>
      </Tooltip>
    </GridRow>
  );
};

export default FormLabel;
