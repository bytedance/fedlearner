import { Refresh } from 'components/IconPark';
import { NodeDataRaw } from 'components/WorkflowJobsFlowChart/helpers';
import React, { FC, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';
import { fetchJobLogs } from 'services/workflow';
import styled from 'styled-components';
import { WorkflowExecutionDetails } from 'typings/workflow';

const LogsPanel = styled.pre`
  padding: 15px;
  height: 350px;
  margin-bottom: 20px;
  background-color: #111;
  border-radius: 4px;
  color: #fefefe;
  text-shadow: 0 0 2px #001716, 0 0 3px #03edf975, 0 0 5px #03edf975, 0 0 8px #03edf975;
  overflow-y: auto;
  white-space: pre-wrap;
  overscroll-behavior: contain;
`;

type Props = {
  enabled: boolean;
  job: NodeDataRaw;
  workflow?: WorkflowExecutionDetails;
};

const JobExecutionLogs: FC<Props> = ({ job, workflow, enabled }) => {
  const panelRef = useRef<HTMLPreElement>();
  const { t } = useTranslation();

  const logsQuery = useQuery(['getJobLogs', job.name], getLogs, {
    refetchOnWindowFocus: true,
    retry: 2,
    refetchInterval: 4000,
    enabled,
  });

  const logs = logsQuery.data?.data || [];

  useEffect(() => {
    if (panelRef.current) {
      panelRef.current.scrollTo({
        top: panelRef.current.scrollHeight,
        behavior: logsQuery.isInitialData ? 'smooth' : undefined,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logs]);

  const isEmpty = logs.length === 0;

  return (
    <>
      <h3>{t('workflow.label_job_logs')}</h3>
      <LogsPanel ref={panelRef as any}>
        {logsQuery.isLoading ? (
          <Refresh spin style={{ fontSize: '20px' }} />
        ) : isEmpty ? (
          'Ooops! No logs at the moment'
        ) : (
          logsQuery.data?.data.join('\n')
        )}
      </LogsPanel>
    </>
  );

  async function getLogs() {
    if (!job.name) {
      return { data: ['Job name invalid!'] };
    }

    // TODO: find a better way to distinguish job-def-name and job-execution-name
    const jobExecutionName = workflow?.jobs!.find((jobExeInfo) => {
      return jobExeInfo.name.endsWith(job.name);
    })?.name;

    return fetchJobLogs(jobExecutionName || `${workflow?.name.trim()}-${job.name.trim()}`, {
      startTime: 0,
      maxLines: 500,
    }).catch((error) => ({
      data: [error.message],
    }));
  }
};

export default JobExecutionLogs;
