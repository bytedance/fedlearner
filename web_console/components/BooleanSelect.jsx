import React from 'react';
import { Select } from '@zeit-ui/react';

const options = [
  { label: 'True', value: 'true' },
  { label: 'False', value: 'false' },
]

export default function ClientTicketSelect(props) {
  const actualValue = props.value.toString() || 'true'
  const actualOnChange = (value) => {
    props.onChange(value === 'true');
  };
  return (
    <Select {...props} initialValue={actualValue} value={actualValue} onChange={actualOnChange}>
      {options.map((x) => <Select.Option key={x.value} value={x.value}>{x.label}</Select.Option>)}
    </Select>
  );
}
