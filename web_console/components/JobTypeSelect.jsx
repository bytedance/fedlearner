import React from 'react';
import { Select } from '@zeit-ui/react';
import { JOB_TYPE } from '../constants/job';

export default function JobTypeSelect(props) {
  const options = JOB_TYPE.map((x) => ({ label: x, value: x }));
  return (
    <Select {...props}>
      {options.map((x) => <Select.Option key={x.value} value={x.value}>{x.label}</Select.Option>)}
    </Select>
  );
}
