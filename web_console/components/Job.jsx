import React, { useCallback } from 'react';
import { Description, Button } from '@zeit-ui/react';
import useSWR from 'swr';

import { fetcher } from '../libs/http';
import { handleStatus } from '../utils/job';
import JobCommonInfo, { jsonHandledPopover } from './JobCommonInfo';

export default function Job({id, ...props}) {
  const { data: jobData } = useSWR(id ? `job/${id}` : null, fetcher);
  const job = jobData ? jobData.data : null;

  const onSubmit = useCallback(() => {}, [])
  const onStop = useCallback(() => {}, [])

  return (
    <JobCommonInfo job={job}>
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
        job?.status?.appState
          ? handleStatus(job?.status?.appState) === 'Running'
              ? <Button size="small" auto type='error' onClick={onStop}>Stop</Button>
              : <Button size="small" auto onClick={onSubmit}>Submit</Button>
          : <Button size="small" auto disabled>Submit</Button>
      }
    </JobCommonInfo>
  );
}
