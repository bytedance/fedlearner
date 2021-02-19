import { NodeDataRaw } from 'components/WorkflowJobsFlowChart/types';
import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchJobLogs } from 'services/workflow';
import styled from 'styled-components';
import { WorkflowExecutionDetails } from 'typings/workflow';
import PrintLogs from 'components/PrintLogs';

const Container = styled.div`
  position: relative;
  margin-bottom: 20px;
`;
const PrintJobLogs = styled(PrintLogs)`
  border-radius: 4px;
`;

type Props = {
  enabled: boolean;
  job: NodeDataRaw;
  workflow?: WorkflowExecutionDetails;
};

const JobExecutionLogs: FC<Props> = ({ job, workflow, enabled }) => {
  const { t } = useTranslation();

  // TODO: find a better way to distinguish job-def-name and job-execution-name
  const jobExecutionName = workflow?.jobs!.find((jobExeInfo) => {
    return jobExeInfo.name.endsWith(job.name);
  })?.name;

  return (
    <Container>
      <h3>{t('workflow.label_job_logs')}</h3>

      <PrintJobLogs
        height="350"
        queryKey={['getJobLogs', jobExecutionName]}
        logsFetcher={getLogs}
        refetchInterval={5000}
        enabled={enabled}
        fullscreenVisible
        onFullscreenClick={goFullScreen}
      />
    </Container>
  );

  async function getLogs() {
    if (!job.name) {
      return { data: ['Job name invalid!'] };
    }

    return fetchJobLogs(jobExecutionName || `${workflow?.name.trim()}-${job.name.trim()}`, {
      startTime: 0,
      maxLines: 500,
    }).catch((error) => ({
      data: [error.message],
    }));
  }

  async function goFullScreen() {
    window.open(`/v2/logs/job/${jobExecutionName}`, '_blank noopener');
  }
};

export default JobExecutionLogs;
