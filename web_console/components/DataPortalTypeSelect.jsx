import React from 'react';
import { Select } from '@zeit-ui/react';

export default function DataPortalTypeSelect(props) {
  const options = [
    { label: 'Streaming', value: 'Streaming' },
    { label: 'PSI', value: 'PSI' },
  ];
  return (
    <Select {...props}>
      {options.map((x) => <Select.Option key={x.value} value={x.value}>{x.label}</Select.Option>)}
    </Select>
  );
}
