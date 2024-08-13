import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import React, { FC, useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchJobLogs, fetchJobEvents, fetchPeerJobEvents } from 'services/workflow';
import styled from './JobExecutionLogs.module.less';
import { WorkflowExecutionDetails } from 'typings/workflow';
import PrintLogs from 'components/PrintLogs';
import { Grid, Radio } from '@arco-design/web-react';

const Row = Grid.Row;

type Props = {
  enabled: boolean;
  job: JobNodeRawData;
  isPeerSide: boolean;
  workflow?: WorkflowExecutionDetails;
  participantId?: ID;
};

enum LogType {
  Logs,
  Events,
}

const JobExecutionLogs: FC<Props> = ({ job, enabled, isPeerSide, workflow, participantId }) => {
  const { t } = useTranslation();
  const [currType, setType] = useState(isPeerSide ? LogType.Events : LogType.Logs);

  const fetchLogsOrEvents = useCallback(
    async (maxLines = 5000) => {
      if (isPeerSide) {
        if (!job.k8sName) {
          return { data: ['K8s Job name invalid!'] };
        }

        return fetchPeerJobEvents(workflow?.uuid!, job.k8sName!, participantId ?? 0, {
          maxLines,
        }).catch((error) => ({
          data: [`[Error occurred during fetchPeerJobEvents]: \n\n${error.message}`],
        }));
      }

      if (!job.id) {
        return { data: ['Job ID invalid!'] };
      }

      if (currType === LogType.Events) {
        return fetchJobEvents(job.id, {
          maxLines,
        }).catch((error) => ({
          data: [`[Error occurred during fetchJobEvents]: \n\n${error.message}`],
        }));
      }

      return fetchJobLogs(job.id, {
        maxLines,
      }).catch((error) => ({
        data: [`[Error occurred during fetchJobLogs]: \n\n${error.message}`],
      }));
    },
    [currType, isPeerSide, job.id, job.k8sName, workflow?.uuid, participantId],
  );

  return (
    <div className={styled.container}>
      <Row align="center" className={styled.heading_row}>
        <h3 className={styled.heading}>{t('workflow.label_job_logs')}</h3>

        <Radio.Group value={currType} size="small" onChange={onTypeChange} type="button">
          {!isPeerSide && <Radio value={LogType.Logs}>Logs</Radio>}
          <Radio value={LogType.Events}>Events</Radio>
        </Radio.Group>
      </Row>

      <PrintLogs
        height="350"
        queryKey={['getJobLogs', currType, job.id]}
        logsFetcher={fetchLogsOrEvents}
        refetchInterval={5000}
        enabled={enabled}
        fullscreenVisible
        onFullscreenClick={goFullScreen}
      />
    </div>
  );

  async function goFullScreen() {
    if (isPeerSide) {
      return window.open(
        `/v2/logs/job/events/peer/${job.k8sName}/${workflow?.uuid}/${participantId ?? ''}`,
        '_blank noopener',
      );
    }

    if (currType === LogType.Events) {
      return window.open(`/v2/logs/job/events/${job.id}`, '_blank noopener');
    }

    window.open(`/v2/logs/job/${job.id}`, '_blank noopener');
  }

  function onTypeChange(value: any) {
    setType(value);
  }
};

export default JobExecutionLogs;
