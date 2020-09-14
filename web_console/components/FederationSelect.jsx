import React from 'react';
import { Select } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';

export default function FederationSelect(props) {
  const { data } = useSWR('federations', fetcher);
  const federations = data ? data.data : [];
  // FIXME: use id for value
  const actualValue = federations.find((x) => x.id === props.value)?.name;
  const actualOnChange = (value) => {
    const federation = federations.find((x) => x.name === value);
    props.onChange(federation.id);
  };
  return (
    <Select {...props} initialValue={actualValue} value={actualValue} onChange={actualOnChange}>
      {federations.map((x) => <Select.Option key={x.name} value={x.name}>{x.trademark}</Select.Option>)}
    </Select>
  );
}
