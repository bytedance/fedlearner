import React, { FC } from 'react';
import { Select } from '@arco-design/web-react';

type Props = {
  value?: string;
  onChange?: any;
};

const TimerNameInput: FC<Props> = ({ value, onChange }) => {
  return (
    <Select
      mode="multiple"
      allowCreate={true}
      defaultValue={value?.split(',')}
      onChange={onTimersChange}
      placeholder="Timers"
      notFoundContent={<span style={{ paddingLeft: '10px' }}>{'输入多个 timer 名称'}</span>}
    />
  );

  function onTimersChange(val: string[]) {
    onChange && onChange(val.join(','));
  }
};

export default TimerNameInput;
