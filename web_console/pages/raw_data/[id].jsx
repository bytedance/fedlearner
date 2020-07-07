import React from 'react';
import { Description } from '@zeit-ui/react';
import useSWR from 'swr';
import { useRouter } from 'next/router';

import { fetcher } from '../../libs/http';
import JobCommonInfo, { jsonHandledPopover } from '../../components/JobCommonInfo';

export default function RawDataJob() {
  const router = useRouter();
  const { query } = router;
  const { data } = useSWR(`raw_data/${query.id}`, fetcher);
  const rawData = data ? data.data : null;

  return (
    <JobCommonInfo job={rawData}>
      <Description
        title="Input"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.input, 26)}
      />
      <Description
        title="Output"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.output, 26)}
      />
      <Description
        title="Context"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.context)}
      />
      <Description
        title="Comment"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.comment, 26)}
      />
    </JobCommonInfo>
  );
}
