import React, { FC } from 'react';
import styled from 'styled-components';
import { Tooltip, Tag } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';

const Container = styled.div`
  display: flex;
  align-items: center;
  font-size: 13px;
  line-height: 1;

  &::before {
    content: '●';
    margin-right: 6px;
    font-size: 20px;
    color: var(--color, #e0e0e0);
  }

  &.is-unknown {
    --color: var(--gray3);
  }
  &.is-success {
    --color: #00bab2;
  }
  &.is-warning {
    --color: var(--orange6);
  }
  &.is-error {
    --color: #fd5165;
  }
  &.is-processing {
    --color: var(--primaryColor);
  }
`;
const QuestionMark = styled(QuestionCircleOutlined)`
  width: 12px;
  height: 12px;
  color: var(--gray6);
`;

export type StateTypes = 'processing' | 'success' | 'warning' | 'error' | 'default';
type Props = {
  tip?: string;
  type: StateTypes;
  text: string;
  tag?: boolean;
};

const StateIndicator: FC<Props> = ({ text, type = 'default', tip, tag }) => {
  if (tag) {
    return <Tag color={type}>{text}</Tag>;
  }
  return (
    <Container className={`is-${type}`}>
      {text}
      {tip && (
        <Tooltip title={tip}>
          <QuestionMark />
        </Tooltip>
      )}
    </Container>
  );
};

export default StateIndicator;
