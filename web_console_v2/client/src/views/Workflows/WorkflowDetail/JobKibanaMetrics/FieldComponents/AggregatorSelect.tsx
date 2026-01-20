import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { KibanaAggregator, KibanaChartType } from 'typings/kibana';
import { Select } from '@arco-design/web-react';

const AggregatorChoices: Partial<Record<KibanaChartType, any[]>> = {
  [KibanaChartType.Timer]: [
    KibanaAggregator.Average,
    KibanaAggregator.Sum,
    KibanaAggregator.Min,
    KibanaAggregator.Variance,
  ],
  [KibanaChartType.Numeric]: [
    KibanaAggregator.Average,
    KibanaAggregator.Sum,
    KibanaAggregator.Min,
    KibanaAggregator.Variance,
  ],
};

type Props = {
  value?: KibanaAggregator;
  onChange?: any;
  type: KibanaChartType;
};

const AggregatorSelect: FC<Props> = ({ value, onChange, type }) => {
  const { t } = useTranslation();
  const options = AggregatorChoices[type] || [];

  return (
    <Select
      defaultValue={value}
      onChange={onSelectChange}
      placeholder={t('workflow.placeholder_aggregator')}
      allowClear
    >
      {options.map((item) => (
        <Select.Option key={item} value={item}>
          {item}
        </Select.Option>
      ))}
    </Select>
  );

  function onSelectChange(value: KibanaAggregator) {
    onChange && onChange(value);
  }
};

export default AggregatorSelect;
