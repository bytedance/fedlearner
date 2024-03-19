import React, { FC } from 'react';
import { DatePicker } from '@arco-design/web-react';
import { disableFuture } from 'shared/date';
import dayjs from 'dayjs';

type Props = {
  value?: number;
  onChange?: any;
  placeholder?: string;
};

const UnixTimePicker: FC<Props> = ({ value, onChange, placeholder }) => {
  return (
    <DatePicker
      defaultValue={value ? (dayjs.unix(value) as any) : null}
      onChange={onPickerChange as any}
      disabledDate={disableFuture}
      showTime={{ format: 'HH:mm:ss' }}
      placeholder={placeholder}
      style={{ width: '100%' }}
    />
  );

  function onPickerChange(val: number) {
    onChange && onChange(dayjs(val).unix());
  }
};

export default UnixTimePicker;
