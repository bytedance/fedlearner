import { NodeDataRaw } from 'components/WorkflowJobsFlowChart/types';
import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchJobLogs, fetchPeerJobEvents } from 'services/workflow';
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
  isPeerSide: boolean;
  workflow?: WorkflowExecutionDetails;
};

const JobExecutionLogs: FC<Props> = ({ job, enabled, isPeerSide }) => {
  const { t } = useTranslation();

  return (
    <Container>
      <h3>{t('workflow.label_job_logs')}</h3>

      <PrintJobLogs
        height="350"
        queryKey={['getJobLogs', job.id]}
        logsFetcher={getLogs}
        refetchInterval={5000}
        enabled={enabled}
        fullscreenVisible
        onFullscreenClick={goFullScreen}
      />
    </Container>
  );

  async function getLogs() {
    if (isPeerSide) {
      if (!job.k8sName) {
        return { data: ['Job name invalid!'] };
      }

      return fetchPeerJobEvents(job.k8sName!, {
        maxLines: 500,
      }).catch((error) => ({
        data: [error.message],
      }));
    }

    if (!job.id) {
      return { data: ['Job ID invalid!'] };
    }

    return fetchJobLogs(job.id, {
      maxLines: 500,
    }).catch((error) => ({
      data: [error.message],
    }));
  }

  async function goFullScreen() {
    if (isPeerSide) {
      return window.open(`/v2/logs/job/events/peer/${job.k8sName}`, '_blank noopener');
    }
    window.open(`/v2/logs/job/${job.id}`, '_blank noopener');
  }
};

export default JobExecutionLogs;
