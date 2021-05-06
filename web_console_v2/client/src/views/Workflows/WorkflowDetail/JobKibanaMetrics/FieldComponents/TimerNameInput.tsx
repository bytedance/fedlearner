import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { Select } from 'antd';

type Props = {
  value?: string;
  onChange?: any;
};

const TimerNameInput: FC<Props> = ({ value, onChange }) => {
  const { t } = useTranslation();

  return (
    <Select
      mode="tags"
      defaultValue={value?.split(',')}
      onChange={onTimersChange}
      placeholder={t('workflow.placeholder_timers')}
      notFoundContent={t('workflow.placeholder_kibana_timer')}
    />
  );

  function onTimersChange(val: string[]) {
    onChange && onChange(val.join(','));
  }
};

export default TimerNameInput;
