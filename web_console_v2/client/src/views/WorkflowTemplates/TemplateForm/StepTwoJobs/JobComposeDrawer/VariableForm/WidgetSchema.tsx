import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, Input, Button, InputNumber, Switch, Select } from 'antd';
import { useTranslation } from 'react-i18next';
import {
  Variable,
  VariableWidgetSchema,
  VariableComponent,
  VariableValueType,
} from 'typings/variable';
import { PlusCircle, Delete } from 'components/IconPark';
import IconButton from 'components/IconButton';
import ModelCodesEditorButton from 'components/ModelCodesEditorButton';

const WidgetFormItem = styled(Form.Item)`
  .ant-input-number {
    width: 100%;
  }
`;
const DelEnumButton = styled(IconButton)`
  position: absolute;
  top: 4px;
  right: -30px;
`;
const Enum = styled.div`
  position: relative;
`;

const { STRING, CODE } = VariableValueType;

/**
 * NOTE: we are not opeing [Radio, Checkbox, Switch] at the moment,
 * bacause Radio, Checkbox can be replaced with Select
 * and Switch's boolean type value is not supported by server side
 */
const WIDGET_COMPONENTS__supported: Partial<Record<VariableComponent, any>> = {
  [VariableComponent.Input]: { use: Input, label: 'Input - 输入框', type: STRING },
  [VariableComponent.Select]: { use: Select, label: 'Select - 选择器', type: STRING },
  [VariableComponent.NumberPicker]: {
    use: InputNumber,
    label: 'Number - 数字输入框',
    type: STRING, // 'number'
  },
  [VariableComponent.TextArea]: {
    use: Input.TextArea,
    label: 'TextArea - 多行文本输入框',
    type: STRING,
  },
  [VariableComponent.Code]: { use: ModelCodesEditorButton, label: 'Code - 代码', type: CODE },
};

export const componentOptions = Object.entries(WIDGET_COMPONENTS__supported).map(([key, val]) => ({
  value: key,
  label: val.label,
}));

type Props = {
  path: (number | string)[];
  value?: VariableWidgetSchema;
  onChange?: (val: Variable) => any;
};

const WidgetSchema: FC<Props> = ({ path, value }) => {
  const { t } = useTranslation();

  if (!value) return null;
  const data = value;
  const pathToVar = path.slice(0, -1);

  const Widget = WIDGET_COMPONENTS__supported[data.component!]?.use || Input;
  const type = WIDGET_COMPONENTS__supported[data.component!]?.type;
  const widgetHasEnum = _hasEnum(data?.component);
  const isCheckableCompnent = _isCheckableCompnent(data?.component);

  return (
    <div>
      <Form.Item
        name={[...path, 'component']}
        label={t('workflow.label_var_comp')}
        rules={[{ required: true, message: '请选择组件' }]}
      >
        <Select placeholder="请选择组件">
          {componentOptions.map((comp) => {
            return (
              <Select.Option key={comp.value} value={comp.value}>
                {comp.label}
              </Select.Option>
            );
          })}
        </Select>
      </Form.Item>

      <Form.Item hidden name={[...pathToVar, 'type']}>
        <Input value={type} />
      </Form.Item>

      {widgetHasEnum && (
        <Form.Item
          name={[...path, 'enum']}
          label={t('workflow.label_var_enum')}
          rules={[{ required: true, message: '请添加至少一个选项' }]}
        >
          <Form.List name={[...path, 'enum']}>
            {(fields, { add, remove }) => {
              return (
                <div>
                  {fields.map((field, index) => {
                    return (
                      <Enum key={field.key + index}>
                        <Form.Item rules={[{ required: true, message: '填写选项值' }]} {...field}>
                          <Input placeholder={`选项 ${index + 1}`} />
                        </Form.Item>
                        <DelEnumButton
                          circle
                          icon={<Delete />}
                          onClick={() => remove(field.name)}
                        />
                      </Enum>
                    );
                  })}

                  <Button size="small" icon={<PlusCircle />} onClick={() => add()}>
                    添加选项
                  </Button>
                </div>
              );
            }}
          </Form.List>
        </Form.Item>
      )}

      {/* The default value path is outside `widget_schema`, so the temp solution is name.slice(0, -1)  */}
      <WidgetFormItem
        name={[...pathToVar, 'value']}
        label={t('workflow.label_default_val')}
        valuePropName={isCheckableCompnent ? 'checked' : 'value'}
        normalize={formatValue}
      >
        {widgetHasEnum ? (
          <Widget placeholder={t('workflow.placeholder_default_val')} allowClear>
            {widgetHasEnum &&
              (data.enum || []).map((opt: any, index: number) => {
                return (
                  <Select.Option key={opt + index} value={opt}>
                    {opt || '##请填充选项值##'}
                  </Select.Option>
                );
              })}
          </Widget>
        ) : (
          <Widget placeholder={t('workflow.placeholder_default_val')} allowClear />
        )}
      </WidgetFormItem>

      <Form.Item name={[...path, 'tooltip']} label={t('用户输入提示')}>
        <Input placeholder={t('输入提示解释该字段作用')} />
      </Form.Item>

      <Form.Item name={[...path, 'required']} valuePropName="checked" label="是否必填">
        <Switch />
      </Form.Item>
    </div>
  );

  function formatValue(value: any) {
    if (type === CODE) {
      return value;
    }

    if (typeof value === 'string') {
      return value;
    }

    // Due to server only accept string type value
    if (typeof value === 'number') {
      return value.toString();
    }
  }
};

function _hasEnum(comp?: VariableComponent) {
  if (!comp) return false;
  const { Select, Radio, Checkbox } = VariableComponent;
  return [Select, Radio, Checkbox].includes(comp);
}
function _isCheckableCompnent(comp?: VariableComponent) {
  if (!comp) return false;
  const { Switch, Radio, Checkbox } = VariableComponent;
  return [Switch, Radio, Checkbox].includes(comp);
}

export default WidgetSchema;
