import React, { useCallback, useState } from 'react';
import { Description, Button } from '@zeit-ui/react';
import useSWR from 'swr';

import { fetcher } from '../libs/http';
import { updateJobStatus } from '../services/job';
import { handleStatus, JobStatus } from '../utils/job';
import JobCommonInfo, { jsonHandledPopover } from './JobCommonInfo';

function getJobForm(job, status) {
  if (!job.localdata) return {}

  const {
    name, job_type, client_ticket_name,
    server_ticket_name, client_params, server_params
  } = job.localdata

  return {
    status,
    name, job_type, client_ticket_name,
    server_ticket_name, client_params, server_params
  }
}

export default function Job({id, ...props}) {
  const { data: jobData, mutate } = useSWR(id ? `job/${id}` : null, fetcher);
  const job = jobData ? jobData.data : null;

  const [jobStatus, setJobStatus] = useState('')

  const onSubmit = useCallback(async () => {
    await updateJobStatus(id, getJobForm(job, 'started'))
    setJobStatus('')
    mutate()
  }, [])
  const onStop = useCallback(async () => {
    await updateJobStatus(id, getJobForm(job, 'stopped'))
    setJobStatus(JobStatus.Killed)
    mutate()
  }, [])

  return (
    <JobCommonInfo job={job} jobStatus={jobStatus}>
      <Description
        title="Job Type"
        style={{ width: 140 }}
        content={job?.localdata?.job_type || '-'}
      />
      <Description
        title="Client Ticket"
        style={{ width: 140 }}
        content={job?.localdata?.client_ticket_name || '-'}
      />
      <Description
        title="Server Ticket"
        style={{ width: 140 }}
        content={job?.localdata?.server_ticket_name || '-'}
      />
      <Description
        title="Client Params"
        style={{ width: 220 }}
        // content={job?.localdata?.client_params ? JSON.stringify(job.localdata.client_params, null, 2) : '-'}
        content={jsonHandledPopover(job?.localdata?.client_params)}
      />
      <Description
        title="Server Params"
        style={{ width: 220 }}
        // content={job?.localdata?.server_params ? JSON.stringify(job.localdata.server_params, null, 2) : '-'}
        content={jsonHandledPopover(job?.localdata?.server_params)}
      />
      {
        job?.localdata
          ? job.localdata.status === 'started'
              ? <Button size="small" auto type='error' onClick={onStop}>Stop</Button>
              : <Button size="small" auto onClick={onSubmit}>Submit</Button>
          : <Button size="small" auto disabled>Submit</Button>
      }
    </JobCommonInfo>
  );
}
