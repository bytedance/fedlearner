import React, { FC, useContext, useState } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { Form, Select, Input, Grid, Button, Switch } from '@arco-design/web-react';
import { KibanaChartType, KibanaQueryFields, KibanaQueryParams } from 'typings/kibana';
import { JobType } from 'typings/job';
import IntervalInput from './FieldComponents/IntervalInput';
import XAxisInput from './FieldComponents/XAxisInput';
import JsonStringInput from './FieldComponents/JsonStringInput';
import UnixTimePicker from './FieldComponents/UnixTimePicker';
import TimerNameInput from './FieldComponents/TimerNameInput';
import AggregatorSelect from './FieldComponents/AggregatorSelect';
import GridRow from 'components/_base/GridRow';
import FormLabel from 'components/FormLabel';
import { IconShareInternal } from '@arco-design/web-react/icon';
import { JobExecutionDetailsContext } from '../JobExecutionDetailsDrawer';

const Row = Grid.Row;
const Col = Grid.Col;

const Container = styled.div``;

const FieldToComponentMap: Partial<Record<KibanaQueryFields, { use: any; help?: string }>> = {
  [KibanaQueryFields.interval]: { use: IntervalInput },
  [KibanaQueryFields.x_axis_field]: {
    use: XAxisInput,
    help: '数据分桶的桶长度',
  },
  [KibanaQueryFields.query]: { use: JsonStringInput },
  [KibanaQueryFields.start_time]: { use: UnixTimePicker },
  [KibanaQueryFields.end_time]: { use: UnixTimePicker },
  [KibanaQueryFields.numerator]: {
    use: JsonStringInput,
    help: '语法同过滤条件，过滤出符合条件的数据，其数量作为分子',
  },
  [KibanaQueryFields.denominator]: {
    use: JsonStringInput,
    help: '语法同过滤条件，过滤出符合条件的数据，其数量作为分母',
  },
  [KibanaQueryFields.aggregator]: { use: AggregatorSelect },
  [KibanaQueryFields.value_field]: { use: Input },
  [KibanaQueryFields.timer_names]: {
    use: TimerNameInput,
    help: '计时器名称，可输入多个',
  },
  [KibanaQueryFields.split]: {
    use: Switch,
    help: '是否分为多张图表绘制',
  },
};

const chartTypeToFormMap = {
  [KibanaChartType.Rate]: {
    onlyFor: [JobType.DATA_JOIN],
    fields: [
      KibanaQueryFields.interval,
      KibanaQueryFields.x_axis_field,
      KibanaQueryFields.query,
      KibanaQueryFields.start_time,
      KibanaQueryFields.end_time,
    ],
  },
  [KibanaChartType.Ratio]: {
    onlyFor: undefined,
    fields: [
      KibanaQueryFields.interval,
      KibanaQueryFields.numerator,
      KibanaQueryFields.denominator,
      KibanaQueryFields.x_axis_field,
      KibanaQueryFields.query,
      KibanaQueryFields.start_time,
      KibanaQueryFields.end_time,
    ],
  },
  [KibanaChartType.Numeric]: {
    onlyFor: undefined,
    fields: [
      KibanaQueryFields.interval,
      KibanaQueryFields.x_axis_field,
      KibanaQueryFields.query,
      KibanaQueryFields.start_time,
      KibanaQueryFields.end_time,
      KibanaQueryFields.value_field,
      KibanaQueryFields.aggregator,
    ],
  },
  [KibanaChartType.Time]: {
    onlyFor: undefined,
    fields: [
      KibanaQueryFields.interval,
      KibanaQueryFields.query,
      KibanaQueryFields.start_time,
      KibanaQueryFields.end_time,
    ],
  },
  [KibanaChartType.Timer]: {
    onlyFor: undefined,
    fields: [
      KibanaQueryFields.timer_names,
      KibanaQueryFields.split,
      KibanaQueryFields.interval,
      KibanaQueryFields.x_axis_field,
      KibanaQueryFields.query,
      KibanaQueryFields.start_time,
      KibanaQueryFields.end_time,
      KibanaQueryFields.aggregator,
    ],
  },
};

type Props = {
  types: KibanaChartType[];
  onPreview: any;
  onNewWindowPreview: any;
  onConfirm: any;
};

const KibanaParamsForm: FC<Props> = ({ types, onPreview, onNewWindowPreview, onConfirm }) => {
  const { t } = useTranslation();

  const initialValues = {
    type: types[0],
  };
  const { isPeerSide } = useContext(JobExecutionDetailsContext);

  const [formData, setFormData] = useState<KibanaQueryParams>(initialValues);

  const [formInstance] = Form.useForm<KibanaQueryParams>();

  const chartType = formData.type as KibanaChartType;

  const fieldsConfig = chartTypeToFormMap[chartType];

  return (
    <Container>
      <Form
        form={formInstance}
        layout="vertical"
        initialValues={initialValues}
        onSubmit={onFinish}
        onValuesChange={onValuesChange}
      >
        <Row gutter={20}>
          <Col span={12}>
            <Form.Item label="Type" field="type">
              <Select>
                {types.map((type) => (
                  <Select.Option key={type} value={type}>
                    {type}
                  </Select.Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          {fieldsConfig &&
            fieldsConfig.fields.map((field) => {
              const Component = FieldToComponentMap[field]?.use || Input;
              return (
                <Col key={field} span={12}>
                  <Form.Item
                    label={<FormLabel label={field} tooltip={FieldToComponentMap[field]?.help} />}
                    field={field}
                  >
                    <Component type={chartType} />
                  </Form.Item>
                </Col>
              );
            })}
        </Row>

        <Form.Item>
          <GridRow gap={16} top="12" justify="end">
            {!isPeerSide && (
              <Button type="text" icon={<IconShareInternal />} onClick={onNewWindowPreviewClick}>
                {t('workflow.btn_preview_kibana_fullscreen')}
              </Button>
            )}

            <Button onClick={onPreviewClick}>{t('workflow.btn_preview_kibana')}</Button>
            <Button type="primary" htmlType="submit" size="small">
              {t('confirm')}
            </Button>
          </GridRow>
        </Form.Item>
      </Form>
    </Container>
  );

  function onFinish(values: KibanaQueryParams) {
    onConfirm(values);
  }
  function onValuesChange(_: any, values: KibanaQueryParams) {
    setFormData(values);
  }
  function onPreviewClick() {
    onPreview(formInstance.getFieldsValue());
  }
  function onNewWindowPreviewClick() {
    onNewWindowPreview(formInstance.getFieldsValue());
  }
};

export default KibanaParamsForm;
