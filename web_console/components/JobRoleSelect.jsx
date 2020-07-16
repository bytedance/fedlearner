import React from 'react';
import { Select } from '@zeit-ui/react';

export default function JobRoleSelect(props) {
  const options = [
    { label: 'Leader', value: 'Leader' },
    { label: 'Follower', value: 'Follower' },
  ];
  return (
    <Select {...props}>
      {options.map((x) => <Select.Option key={x.value} value={x.value}>{x.label}</Select.Option>)}
    </Select>
  );
}
