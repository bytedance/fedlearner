import React, { useEffect } from 'react';
import { Select } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';

let rendered = false

export default function FederationSelect(props) {
  const { data } = useSWR('federations', fetcher);
  const federations = data ? data.data : [];
  // FIXME: use id for value
  const actualValue = federations.find((x) => x.id === props.value)?.name;
  const actualOnChange = (value) => {
    const federation = federations.find((x) => x.name === value);
    props.onChange(federation.id);
  };

  !rendered
    && props.initTrigerChange
    && props.value
    && props.onChange(props.value)

  rendered = true

  // reset flag
  useEffect(() => () => rendered = false, [])

  return (
    <Select {...props} initialValue={actualValue} value={actualValue} onChange={actualOnChange}>
      {federations.map((x) => <Select.Option key={x.name} value={x.name}>{x.trademark || x.name}</Select.Option>)}
    </Select>
  );
}
