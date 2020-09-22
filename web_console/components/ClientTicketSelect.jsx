import React, { useCallback } from 'react';
import { Select } from '@zeit-ui/react';
import useSWR from 'swr';
import { fetcher } from '../libs/http';
import { JOB_TYPE_CLASS } from '../constants/job'

let filter = () => true
export default function ClientTicketSelect({type, ...props}) {
  const { data } = useSWR('tickets', fetcher);

  if (type) {
    filter = el => JOB_TYPE_CLASS[type].some(t => el.job_type === t)
  }

  const tickets = data
    ? data.data.filter(filter)
    : [];

  // const actualValue = tickets.find((x) => x.name === props.value)?.value;
  const actualValue = props.value || ''
  const actualOnChange = (value) => {
    const ticket = tickets.find((x) => x.name === value);
    props.onChange(ticket.name);
  };
  return (
    <Select {...props} initialValue={actualValue} value={actualValue} onChange={actualOnChange}>
      {tickets.map((x) => <Select.Option key={x.name} value={x.name}>{x.name}</Select.Option>)}
    </Select>
  );
}
