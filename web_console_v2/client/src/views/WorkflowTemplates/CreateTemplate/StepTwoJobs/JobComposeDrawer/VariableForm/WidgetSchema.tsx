import React, { FC } from 'react';
import styled from 'styled-components';
import { Form, Input, Button, InputNumber, Checkbox, Switch, Select, Col, Radio } from 'antd';
import { useTranslation } from 'react-i18next';
import { Variable, VariableWidgetSchema, VariableComponent } from 'typings/variable';
import { PlusCircle, Delete } from 'components/IconPark';
import IconButton from 'components/IconButton';

type Props = {
  name: (number | string)[];
  value?: VariableWidgetSchema;
  onChange?: (val: Variable) => any;
};

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

export const componentsMap: Partial<Record<VariableComponent, any>> = {
  [VariableComponent.Input]: Input,
  [VariableComponent.Select]: Select,
  [VariableComponent.NumberPicker]: InputNumber,
  [VariableComponent.Code]: Input.TextArea,
  // Radio and Checkbox are replaceable with Select
  // [VariableComponent.Radio]: Radio,
  // [VariableComponent.Checkbox]: Checkbox,
  [VariableComponent.TextArea]: Input.TextArea,
  [VariableComponent.Switch]: Switch,
};

const componentOptions = Object.keys(componentsMap);

const WidgetSchema: FC<Props> = ({ name, value }) => {
  const data = value!;
  const { t } = useTranslation();

  const Widget = componentsMap[data.component!];
  const widgetHasEnum = _hasEnum(data.component);
  const isCheckableCompnent = _isCheckableCompnent(data.component);

  return (
    <div>
      <Form.Item required name={[...name, 'component']} label={t('workflow.label_var_comp')}>
        <Select>
          {componentOptions.map((comp) => {
            return (
              <Select.Option key={comp} value={comp}>
                {comp}
              </Select.Option>
            );
          })}
        </Select>
      </Form.Item>

      {widgetHasEnum && (
        <Form.Item
          name={[...name, 'enum']}
          label={t('workflow.label_var_enum')}
          rules={[{ required: true, message: '请添加至少一个选项' }]}
        >
          <Form.List name={[...name, 'enum']}>
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

      <WidgetFormItem
        name={[...name, 'value']}
        label={t('workflow.label_default_val')}
        valuePropName={isCheckableCompnent ? 'checked' : 'value'}
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
    </div>
  );
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
