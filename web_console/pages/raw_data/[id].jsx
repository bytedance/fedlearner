import React, { useCallback, useState } from 'react';
import { Description, Button, useToasts } from '@zeit-ui/react';
import useSWR from 'swr';
import { useRouter } from 'next/router';

import { submitRawData } from '../../services/raw_data';
import { fetcher } from '../../libs/http';
import JobCommonInfo, { jsonHandledPopover } from '../../components/JobCommonInfo';
import { FLAppStatus } from '../../utils/job';

export default function RawDataJob() {
  const router = useRouter();
  const { query } = router;
  const { data } = useSWR(`raw_data/${query.id}`, fetcher);
  const rawData = data ? data.data : null;

  const [loading, setLoading] = useState(false);
  const [, setToast] = useToasts();
  const submit = useCallback(() => {
    setLoading(true);
    submitRawData(rawData?.localdata?.id).then((res) => {
      setLoading(false);
      if (res.error) {
        setToast({
          text: res.error,
          type: 'error',
        });
      }
    }).catch(() => setLoading(false));
  }, [rawData?.localdata?.id]);

  return (
    <JobCommonInfo job={rawData}>
      <Description
        title="Federation"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.federation?.name)}
      />
      <Description
        title="Output Partition Num"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.output_partition_num)}
      />
      <Description
        title="Data Portal Type"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.data_portal_type)}
      />
      <Description
        title="Input"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.input, 22)}
      />
      <Description
        title="Output"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.output, 22)}
      />
      <Description
        title="Context"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.context)}
      />
      <Description
        title="Comment"
        style={{ width: 220 }}
        content={jsonHandledPopover(rawData?.localdata?.comment, 22)}
      />
      <Button
        auto
        size="small"
        onClick={submit}
        disabled={!(rawData?.localdata?.id) || rawData?.status?.appState === FLAppStatus.Running}
        loading={loading}
      >Submit Raw Data</Button>
    </JobCommonInfo>
  );
}
