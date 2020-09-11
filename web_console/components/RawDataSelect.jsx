import React from 'react';
import { Select } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';

export default function RawDataSelect(props) {
  const { data } = useSWR('raw_datas', fetcher);
  const rawDatas = data ? data.data : [];
  const actualValue = typeof props.value === 'string'
    ? props.value : props.value?.name
  const actualOnChange = (value) => {
    const rawData = rawDatas.find((x) => x.name === value);
    props.onChange(rawData);
  };
  return (
    <Select {...props} value={actualValue} onChange={actualOnChange}>
      {rawDatas.map((x) => <Select.Option key={x.name} value={x.name}>{x.name}</Select.Option>)}
    </Select>
  );
}
