import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import styled from 'styled-components';

const ResultPanel = styled.pre`
  padding: 15px;
  height: 250px;
  margin-bottom: 20px;
  background-color: #111;
  border-radius: 4px;
  color: #fefefe;
  text-shadow: 0 0 2px #001716, 0 0 3px #03edf975, 0 0 5px #03edf975, 0 0 8px #03edf975;
`;

const JobExecutionLogs: FC = () => {
  const { t } = useTranslation();

  return (
    <>
      <h3>{t('workflow.label_job_logs')}</h3>
      <ResultPanel>Coming soon</ResultPanel>
    </>
  );
};

export default JobExecutionLogs;
