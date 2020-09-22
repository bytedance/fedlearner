import React, { useEffect } from 'react';
import { Select } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';

let initialUpdated = false

export default function RawDataSelect(props) {
  const { data } = useSWR('raw_datas', fetcher);
  const rawDatas = data ? data.data : [];
  const actualValue = typeof props.value === 'string'
    ? props.value : props.value?.name
  const actualOnChange = (value) => {
    const rawData = rawDatas.find((x) => x.name === value);
    props.onChange(rawData);
  };

  if (!initialUpdated) {
    typeof props.value === 'string'
      && rawDatas.length > 0
      && actualOnChange(props.value)

    initialUpdated = true
  }

  useEffect(() => () => initialUpdated = false, [])

  return (
    <Select {...props} initialValue={actualValue} value={actualValue} onChange={actualOnChange}>
      {rawDatas.map((x) => <Select.Option key={x.name} value={x.name}>{x.name}</Select.Option>)}
    </Select>
  );
}
