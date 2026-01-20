import React, { FC, useEffect } from 'react';
import styled from 'styled-components';
import { useToggle } from 'react-use';
import CronTimePicker, { parseCron, PickerValue, toCron } from 'components/CronTimePicker';
import { Switch } from '@arco-design/web-react';
import i18n from 'i18n';

const SwitchContainer = styled.div`
  margin-bottom: 16px;
`;

type Props = {
  value?: string;
  onChange?: (value: string) => void;
};

const ScheduleTaskSetter: FC<Props> = (prop: Props) => {
  const { value, onChange } = prop;
  const isEnabled = !!value;
  const [inputVisible, toggleVisible] = useToggle(isEnabled);

  useEffect(() => {
    toggleVisible(isEnabled);
  }, [isEnabled, toggleVisible]);

  const onSwitchChange = (checked: boolean) => {
    toggleVisible(checked);
    onValueChange(checked ? 'null' : '');
  };
  const onValueChange = (val: string) => {
    onChange && onChange(val);
  };

  return (
    <>
      <SwitchContainer>
        <Switch checked={inputVisible} onChange={onSwitchChange} />
      </SwitchContainer>

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
};
export function scheduleTaskValidator(val: any, cb: (error?: string) => void) {
  // !val means switch be set to close status --> validate to pass
  // val !== 'null' means has chosen correct time and validate to pass
  if (!val || val !== 'null') {
    return cb();
  }
  return cb(i18n.t('model_center.msg_time_required'));
}

export default ScheduleTaskSetter;
