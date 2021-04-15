import React, { FC } from 'react';
import styled from 'styled-components';
import { InputNumber, Switch } from 'antd';
import { useToggle } from 'react-use';

export const MIN_SCHEDULED_MINUTES = 10;

const SwitchContainer = styled.div`
  margin-top: 5px;
  margin-bottom: 15px;
`;

type Props = {
  value?: number;
  onChange?: (v: number) => void;
};

const ScheduledWorkflowRunning: FC<Props> = ({ value, onChange }) => {
  const [inputVisible, toggleVisible] = useToggle(value !== -1 || value >= 10);

  return (
    <>
      <SwitchContainer>
        <Switch checked={inputVisible} onChange={onSwitchChange} />
      </SwitchContainer>

      {inputVisible && (
        <InputNumber
          min={MIN_SCHEDULED_MINUTES}
          value={value}
          onChange={onValueChange}
          formatter={(value: any) => `${value}min`}
          parser={(value: any) => value.replace('min', '')}
        />
      )}
    </>
  );

  function onSwitchChange(val: boolean) {
    toggleVisible(val);

    if (val === false) {
      onChange && onChange(-1);
    } else {
      onChange && onChange(MIN_SCHEDULED_MINUTES);
    }
  }
  function onValueChange(val: number) {
    onChange && onChange(val);
  }
};

export function scheduleIntervalValidator(_: any, value: number) {
  if (value >= MIN_SCHEDULED_MINUTES || value === -1) {
    return Promise.resolve();
  }
  return Promise.reject();
}

export default ScheduledWorkflowRunning;
