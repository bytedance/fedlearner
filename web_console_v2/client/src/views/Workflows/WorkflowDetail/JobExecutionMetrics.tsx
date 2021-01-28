import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import styled from 'styled-components';

const Container = styled.div`
  margin-top: 30px;
`;
const ResultPanel = styled.div`
  padding: 15px;
  height: 250px;
  margin-bottom: 20px;
  background-color: #17114f;
  border-radius: 4px;
  color: #fefefe;
`;

const JobExecutionMetrics: FC = () => {
  const { t } = useTranslation();
  return (
    <Container>
      <h3>{t('workflow.label_job_metrics')}</h3>
      <ResultPanel />
    </Container>
  );
};

export default JobExecutionMetrics;
