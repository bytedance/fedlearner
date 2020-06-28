import React from 'react';
import { Select } from '@zeit-ui/react';

export default function JobTypeSelect(props) {
  const options = [
    { label: 'psi_data_join', value: 'psi_data_join' },
    { label: 'tree_model_train', value: 'tree_model_train' },
  ];
  return (
    <Select {...props}>
      {options.map((x) => <Select.Option key={x.value} value={x.value}>{x.label}</Select.Option>)}
    </Select>
  );
}
