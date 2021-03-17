import React, { FC } from 'react';
import { Tooltip } from 'antd';
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
};

const FormLabel: FC<Props> = ({ label, tooltip }) => {
  if (!tooltip) {
    return <LabelText>{label}</LabelText>;
  }

  return (
    <GridRow gap="8" role="label">
      <Tooltip title={tooltip}>
        <LabelText>
          {label}
          <QuestionCircle style={{ marginLeft: '5px' }} />
        </LabelText>
      </Tooltip>
    </GridRow>
  );
};

export default FormLabel;
