import { NodeDataRaw } from 'components/WorkflowJobsFlowChart/types';
import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchJobLogs } from 'services/workflow';
import styled from 'styled-components';
import { WorkflowExecutionDetails } from 'typings/workflow';
import PrintLogs from 'components/PrintLogs';
import { findJobExeInfoByJobDef } from 'shared/workflow';

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

  const k8sJobName = job.k8sName || (workflow && findJobExeInfoByJobDef(job, workflow)?.name);

  return (
    <Container>
      <h3>{t('workflow.label_job_logs')}</h3>

      <PrintJobLogs
        height="350"
        queryKey={['getJobLogs', k8sJobName]}
        logsFetcher={getLogs}
        refetchInterval={5000}
        enabled={enabled}
        fullscreenVisible
        onFullscreenClick={goFullScreen}
      />
    </Container>
  );

  async function getLogs() {
    if (!k8sJobName) {
      return { data: ['K8s Job name invalid!'] };
    }

    return fetchJobLogs(k8sJobName || `${workflow?.uuid}-${job.name.trim()}`, {
      startTime: 0,
      maxLines: 500,
    }).catch((error) => ({
      data: [error.message],
    }));
  }

  async function goFullScreen() {
    window.open(`/v2/logs/job/${k8sJobName}`, '_blank noopener');
  }
};

export default JobExecutionLogs;
