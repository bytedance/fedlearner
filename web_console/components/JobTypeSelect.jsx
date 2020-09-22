import React from 'react';
import { Select } from '@zeit-ui/react';
import { JOB_TYPE_CLASS } from '../constants/job';

export default function JobTypeSelect(props) {
  const types = props.type ? JOB_TYPE_CLASS[props.type] : JOB_TYPE_CLASS.all
  const options = types.map((x) => ({ label: x, value: x }));
  return (
    <Select {...props} initialValue={props.value} >
      {options.map((x) => <Select.Option key={x.value} value={x.value}>{x.label}</Select.Option>)}
    </Select>
  );
}
