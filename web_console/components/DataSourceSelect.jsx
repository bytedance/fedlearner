import React from 'react';
import { Select, Popover } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';
import { JOB_TYPE_CLASS } from '../constants/job'

export default function DataSourceSelect({type, ...props}) {

  const filter = el => JOB_TYPE_CLASS.datasource.some(t => el.localdata?.job_type === t)

  const { data } = useSWR(`jobs`, fetcher);
  const jobs = data?.data?.filter(filter) || []

  const actualValue = jobs.find((x) => x.localdata?.name === props.value)?.localdata?.name;
  const actualOnChange = (value) => {
    props.onChange(value);
  };

  return (
    <Select {...props} initialValue={actualValue} value={actualValue} onChange={actualOnChange}>
      {
        jobs.map((x) =>
          <Select.Option key={x.localdata.name} value={x.localdata.name}>
              {x.localdata.name}
          </Select.Option>
        )
      }
    </Select>
  );
}
