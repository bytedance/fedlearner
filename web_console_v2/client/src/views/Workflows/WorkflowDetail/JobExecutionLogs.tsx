import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import styled from 'styled-components';

const ResultPanel = styled.div`
  height: 350px;
  background-color: #111;
  border-radius: 4px;
`;

const JobExecutionLogs: FC = () => {
  const { t } = useTranslation();

  return (
    <>
      <h3>{t('workflow.label_job_logs')}</h3>
      <ResultPanel />
    </>
  );
};

export default JobExecutionLogs;
