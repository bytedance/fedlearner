import React, { ReactElement } from 'react';
import styled, { CSSProperties } from 'styled-components';
import { formatTimestamp } from 'shared/date';

const Container = styled.div`
  padding-right: 16px;
  color: var(--gray7);
  font-size: 12px;
  text-align: right;
  line-height: 40px;
`;

interface CreateTimeProps {
  time: number;
  style?: CSSProperties;
}

function CreateTime({ time, style }: CreateTimeProps): ReactElement {
  const _time = formatTimestamp(time);
  return <Container style={style}>{_time}</Container>;
}

export default CreateTime;
