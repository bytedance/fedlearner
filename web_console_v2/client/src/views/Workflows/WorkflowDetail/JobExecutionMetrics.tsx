import React, { FC } from 'react';
import styled from 'styled-components';

const Container = styled.div`
  margin-top: 30px;
`;
const ResultPanel = styled.div`
  height: 300px;
  margin-bottom: 20px;
  background-color: #111;
  border-radius: 4px;
`;

const JobExecutionMetrics: FC = () => {
  return (
    <Container>
      <h3>任务运行结果指标</h3>
      <ResultPanel />
    </Container>
  );
};

export default JobExecutionMetrics;
