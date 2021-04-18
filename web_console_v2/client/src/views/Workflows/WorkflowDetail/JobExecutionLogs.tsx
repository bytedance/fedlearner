import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import React, { FC, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchJobLogs, fetchJobEvents, fetchPeerJobEvents } from 'services/workflow';
import styled from 'styled-components';
import { WorkflowExecutionDetails } from 'typings/workflow';
import PrintLogs from 'components/PrintLogs';
import { Row, Radio, RadioChangeEvent } from 'antd';

const Container = styled.div`
  position: relative;
  margin-bottom: 20px;
`;
const HeadingRow = styled(Row)`
  margin-bottom: 10px;
`;
const Heading = styled.h3`
  margin-bottom: 0;
  margin-right: 10px;
`;
const PrintJobLogs = styled(PrintLogs)`
  border-radius: 4px;
`;

type Props = {
  enabled: boolean;
  job: JobNodeRawData;
  isPeerSide: boolean;
  workflow?: WorkflowExecutionDetails;
};

enum LogType {
  Logs,
  Events,
}

const JobExecutionLogs: FC<Props> = ({ job, enabled, isPeerSide, workflow }) => {
  const { t } = useTranslation();
  const [currType, setType] = useState(isPeerSide ? LogType.Events : LogType.Logs);

  const fetchLogsOrEvents = useCallback(async () => {
    if (isPeerSide) {
      if (!job.k8sName) {
        return { data: ['K8s Job name invalid!'] };
      }

      return fetchPeerJobEvents(workflow?.uuid!, job.k8sName!, {
        maxLines: 500,
      }).catch((error) => ({
        data: [`[Error occurred during fetchPeerJobEvents]: \n\n${error.message}`],
      }));
    }

    if (!job.id) {
      return { data: ['Job ID invalid!'] };
    }

    if (currType === LogType.Events) {
      return fetchJobEvents(job.id, {
        maxLines: 500,
      }).catch((error) => ({
        data: [`[Error occurred during fetchJobEvents]: \n\n${error.message}`],
      }));
    }

    return fetchJobLogs(job.id, {
      maxLines: 500,
    }).catch((error) => ({
      data: [`[Error occurred during fetchJobLogs]: \n\n${error.message}`],
    }));
  }, [currType, isPeerSide, job.id, job.k8sName, workflow?.uuid]);

  return (
    <Container>
      <HeadingRow align="middle">
        <Heading>{t('workflow.label_job_logs')}</Heading>

        <Radio.Group value={currType} size="small" onChange={onTypeChange}>
          {!isPeerSide && <Radio.Button value={LogType.Logs}>Logs</Radio.Button>}
          <Radio.Button value={LogType.Events}>Events</Radio.Button>
        </Radio.Group>
      </HeadingRow>

      <PrintJobLogs
        height="350"
        queryKey={['getJobLogs', currType, job.id]}
        logsFetcher={fetchLogsOrEvents}
        refetchInterval={5000}
        enabled={enabled}
        fullscreenVisible
        onFullscreenClick={goFullScreen}
      />
    </Container>
  );

  async function goFullScreen() {
    if (isPeerSide) {
      return window.open(
        `/v2/logs/job/events/peer/${job.k8sName}/${workflow?.uuid}`,
        '_blank noopener',
      );
    }

    if (currType === LogType.Events) {
      return window.open(`/v2/logs/job/events/${job.id}`, '_blank noopener');
    }

    window.open(`/v2/logs/job/${job.id}`, '_blank noopener');
  }

  function onTypeChange(event: RadioChangeEvent) {
    setType(event.target.value);
  }
};

export default JobExecutionLogs;
