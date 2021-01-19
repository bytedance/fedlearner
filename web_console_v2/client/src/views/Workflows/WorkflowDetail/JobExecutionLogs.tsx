import React, { FC } from 'react';
import styled from 'styled-components';

const ResultPanel = styled.div`
  height: 350px;
  background-color: #111;
  border-radius: 4px;
`;

const JobExecutionLogs: FC = () => {
  return (
    <>
      <h3>任务运行日志</h3>
      <ResultPanel />
    </>
  );
};

export default JobExecutionLogs;
