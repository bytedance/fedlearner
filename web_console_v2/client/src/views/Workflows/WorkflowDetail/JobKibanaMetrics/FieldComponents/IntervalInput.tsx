import React, { FC, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Input, Select } from '@arco-design/web-react';

const { Option } = Select;

type Props = {
  value?: string;
  onChange?: any;
};

const IntervalInput: FC<Props> = ({ value, onChange }) => {
  const { t } = useTranslation();

  const [n, unit] = _parse(value);
  const [localN, setN] = useState(n);
  const [localUnit, setUnit] = useState(n);

  return (
    <Input
      placeholder={t('workflow.placeholder_interval')}
      defaultValue={n}
      onChange={onInputChange}
      addAfter={
        <Select defaultValue={unit} onChange={onSelectChange} style={{ width: '66px' }}>
          <Option value="m">分</Option>
          <Option value="h">小时</Option>
          <Option value="d">天</Option>
          <Option value="w">周</Option>
          <Option value="M">月</Option>
          <Option value="Y">年</Option>
        </Select>
      }
    />
  );
  function onInputChange(value: string) {
    setN(value);

    if (!localUnit) {
      onChange && onChange(undefined);
      return;
    }
    onChange && onChange(value + localUnit);
  }
  function onSelectChange(value: string) {
    setUnit(value);

    if (!localN) {
      onChange && onChange(undefined);
      return;
    }

    onChange && onChange(localN + value);
  }
};

function _parse(val?: string): [any, any] {
  if (!val) return ['', ''];

  const matched = val.match(/^(\d+)([mhdwMy])/g);
  if (!matched) return ['', ''];

  return [matched[1], matched[2]];
}

export default IntervalInput;
