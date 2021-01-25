import React, { FC } from 'react';
import styled from 'styled-components';
import { Tooltip, Tag } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';

const Container = styled.div`
  display: flex;
  align-items: center;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;

  &::before {
    content: '●';
    margin-right: 6px;
    font-size: 20px;
    color: var(--color, #e0e0e0);
  }

  &[color='unknown'] {
    --color: var(--backgroundGray);
  }
  &[color='success'] {
    --color: #00bab2;
  }
  &[color='warning'] {
    --color: var(--orange6);
  }
  &[color='error'] {
    --color: #fd5165;
  }
  &[color='processing'] {
    --color: var(--primaryColor);
  }
`;
const Text = styled.span`
  margin-right: 5px;
`;
const Help = styled.div`
  cursor: help;
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
  let Wrapper = tag ? Tag : Container;

  if (tag) {
    return <Tag color={type}>{text}</Tag>;
  }

  const Content = (
    <Wrapper color={type}>
      <Text>{text}</Text>
      {tip && <QuestionMark />}
    </Wrapper>
  );

  if (tip?.trim()) {
    return (
      <Tooltip title={tip}>
        <Help>{Content}</Help>
      </Tooltip>
    );
  }

  return Content;
};

export default StateIndicator;
