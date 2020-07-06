import React from 'react';
import { Select } from '@zeit-ui/react';
// import useSWR from 'swr';
// import { fetcher } from '../libs/http';

export default function ServerTicketSelect(props) {
  // TODO: get server tickets
  // const { data } = useSWR('tickets/server', fetcher);
  // const tickets = (data && data.data) || [];
  const tickets = [];

  const actualValue = tickets.find((x) => x.name === props.value)?.value;
  const actualOnChange = (value) => {
    const ticket = tickets.find((x) => x.name === value);
    props.onChange(ticket.name);
  };
  return (
    <Select {...props} value={actualValue} onChange={actualOnChange}>
      {tickets.map((x) => <Select.Option key={x.name} value={x.name}>{x.name}</Select.Option>)}
    </Select>
  );
}
