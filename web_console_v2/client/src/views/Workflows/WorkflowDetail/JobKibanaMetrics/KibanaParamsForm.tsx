import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { Form, Select, Input, Row, Col, Button, Switch } from 'antd';
import { KibanaChartType, KibanaQueryFields, KibanaQueryParams } from 'typings/kibana';
import { JobType } from 'typings/job';
import IntervalInput from './FieldComponents/IntervalInput';
import XAxisInput from './FieldComponents/XAxisInput';
import QueryInput from './FieldComponents/QueryInput';
import UnixTimePicker from './FieldComponents/UnixTimePicker';
import TimerNameInput from './FieldComponents/TimerNameInput';
import AggregatorSelect from './FieldComponents/AggregatorSelect';
import GridRow from 'components/_base/GridRow';
import FormLabel from 'components/FormLabel';
import { ShareInternal } from 'components/IconPark';

const Container = styled.div``;

const FieldToComponentMap: Partial<Record<KibanaQueryFields, { use: any; help?: string }>> = {
  [KibanaQueryFields.interval]: { use: IntervalInput },
  [KibanaQueryFields.x_axis_field]: {
    use: XAxisInput,
    help: '数据分桶的桶长度',
  },
  [KibanaQueryFields.query]: { use: QueryInput },
  [KibanaQueryFields.start_time]: { use: UnixTimePicker },
  [KibanaQueryFields.end_time]: { use: UnixTimePicker },
  [KibanaQueryFields.numerator]: {
    use: Input,
    help: '语法同过滤条件，过滤出符合条件的数据，其数量作为分子',
  },
  [KibanaQueryFields.denominator]: {
    use: Input,
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
      KibanaQueryFields.x_axis_field,
      KibanaQueryFields.query,
      KibanaQueryFields.start_time,
      KibanaQueryFields.end_time,
      KibanaQueryFields.numerator,
      KibanaQueryFields.denominator,
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
  jobType: JobType;
  onPreview: any;
  onNewWindowPreview: any;
  onConfirm: any;
};

const KibanaParamsForm: FC<Props> = ({ jobType, onPreview, onNewWindowPreview, onConfirm }) => {
  const { t } = useTranslation();

  const initialValues = {
    type: jobType === JobType.DATA_JOIN ? KibanaChartType.Rate : KibanaChartType.Ratio,
  };

  const [formData, setFormData] = useState<KibanaQueryParams>(initialValues);

  const [formInstance] = Form.useForm<KibanaQueryParams>();

  const chartType = formData.type as KibanaChartType;

  const fieldsConfig = chartTypeToFormMap[chartType];

  return (
    <Container>
      <Form
        form={formInstance}
        layout="vertical"
        size="small"
        initialValues={initialValues}
        onFinish={onFinish}
        onValuesChange={onValuesChange}
      >
        <Row gutter={20}>
          <Col span={12}>
            <Form.Item label="Type" name="type">
              <Select>
                {Object.values(KibanaChartType).map((type) => (
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
                    name={field}
                  >
                    <Component type={chartType} />
                  </Form.Item>
                </Col>
              );
            })}
        </Row>

        <Form.Item>
          <GridRow gap={16} top="12" justify="end">
            <Button
              type="link"
              size="small"
              icon={<ShareInternal />}
              onClick={onNewWindowPreviewClick}
            >
              {t('workflow.btn_preview_kibana_fullscreen')}
            </Button>
            <Button size="middle" onClick={onPreviewClick}>
              {t('workflow.btn_preview_kibana')}
            </Button>
            <Button type="primary" htmlType="submit" size="middle">
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
    onPreview(formInstance.getFieldsValue(true));
  }
  function onNewWindowPreviewClick() {
    onNewWindowPreview(formInstance.getFieldsValue(true));
  }
};

export default KibanaParamsForm;
