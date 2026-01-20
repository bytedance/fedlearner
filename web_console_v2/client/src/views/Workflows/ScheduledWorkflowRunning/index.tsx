import React, { FC, useEffect } from 'react';
import styled from './index.module.less';
import { Switch } from '@arco-design/web-react';
import { useToggle } from 'react-use';
import CronTimePicker, { parseCron, PickerValue, toCron } from 'components/CronTimePicker';

type Props = {
  value?: string;
  onChange?: (value: string) => void;
};

const ScheduledWorkflowRunning: FC<Props> = ({ value, onChange }) => {
  const isEnabled = !!value;
  const [inputVisible, toggleVisible] = useToggle(isEnabled);

  useEffect(() => {
    if (isEnabled) {
      toggleVisible(true);
    }
  }, [isEnabled, toggleVisible]);

  return (
    <>
      <div className={styled.switch_container}>
        <Switch checked={inputVisible} onChange={onSwitchChange} />
      </div>

      {inputVisible && (
        <CronTimePicker
          value={parseCron(value || '')}
          onChange={(value: PickerValue) => {
            onValueChange(toCron(value));
          }}
        />
      )}
    </>
  );

  function onSwitchChange(val: boolean) {
    toggleVisible(val);
    if (val === false) {
      onValueChange('');
    } else {
      onValueChange('null');
    }
  }
  function onValueChange(val: string) {
    onChange && onChange(val);
  }
};
export function scheduleIntervalValidator(value: any, callback: (error?: string) => void) {
  if (!value || value !== 'null') {
    return;
  }
  callback('请选择时间');
}

export default ScheduledWorkflowRunning;
