import React from 'react';
import { Description } from '@zeit-ui/react';
import useSWR from 'swr';
import { useRouter } from 'next/router';

import { fetcher } from '../../libs/http';
import JobCommonInfo, { jsonHandledPopover } from '../../components/JobCommonInfo';

export default function Job() {
  const router = useRouter();
  const { query } = router;
  const { data: jobData } = useSWR(query.id ? `job/${query.id}` : null, fetcher);
  const job = jobData ? jobData.data : null;

  return (
    job ? <JobCommonInfo job={job}>
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
    </JobCommonInfo>
  : null
  );
}
