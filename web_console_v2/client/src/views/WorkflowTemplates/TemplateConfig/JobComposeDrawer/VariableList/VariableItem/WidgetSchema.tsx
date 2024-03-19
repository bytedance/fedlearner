import React, { FC, useCallback, useState } from 'react';
import styled from './WidgetSchema.module.less';
import { set } from 'lodash-es';
import { formatValueToString } from 'shared/helpers';

import { Button, Input, InputNumber, Select, Switch, Form } from '@arco-design/web-react';
import { DatasetPathSelect } from 'components/DatasetSelect';
import IconButton from 'components/IconButton';
import { Delete, PlusCircle } from 'components/IconPark';
import ModelCodesEditorButton from 'components/ModelCodesEditorButton';
import { AlgorithmSelect } from 'components/DoubleSelect';
import EnvsInputForm from './EnvsInputForm';
import YAMLTemplateEditorButton from 'components/YAMLTemplateEditorButton';

import {
  Variable,
  VariableAccessMode,
  VariableComponent,
  VariableValueType,
  VariableWidgetSchema,
} from 'typings/variable';

import { CpuInput, MemInput } from 'components/InputGroup/NumberTextInput';
import { disabeldPeerWritableComponentTypeList } from '.';
import { Tag } from 'typings/workflow';

const { STRING, CODE, LIST, OBJECT, NUMBER } = VariableValueType;

/**
 * NOTE: we are not open to choose [Radio, Checkbox, Switch] at the moment,
 * bacause Radio, Checkbox can be replaced with Select
 * and Switch's boolean type value is not supported by server side yet
 */
const WIDGET_COMPONENTS__supported: Partial<Record<VariableComponent, any>> = {
  [VariableComponent.Input]: {
    use: Input,
    label: 'Input - 输入框',
    type: STRING,
    allowTypeList: [STRING, LIST, OBJECT],
    displayType: STRING,
  },
  [VariableComponent.Select]: {
    use: Select,
    label: 'Select - 选择器',
    type: STRING,
    allowTypeList: [STRING],
    displayType: STRING,
  },
  [VariableComponent.NumberPicker]: {
    use: InputNumber,
    label: 'Number - 数字输入框',
    type: NUMBER,
    allowTypeList: [NUMBER],
    displayType: NUMBER,
  },
  [VariableComponent.CPU]: {
    use: CpuInput,
    label: 'CpuInput - 输入 Cpu 资源参数的输入框',
    type: STRING,
    allowTypeList: [STRING],
    displayType: STRING,
    props: {
      min: 1000,
      max: Number.MAX_SAFE_INTEGER,
    },
  },
  [VariableComponent.MEM]: {
    use: MemInput,
    label: 'MemInput - 输入 Mem 资源参数的输入框',
    type: STRING,
    allowTypeList: [STRING],
    displayType: STRING,
    props: {
      min: 1,
      max: 100,
    },
  },
  [VariableComponent.TextArea]: {
    use: Input.TextArea,
    label: 'TextArea - 多行文本输入框',
    type: STRING,
    allowTypeList: [STRING],
    displayType: STRING,
  },
  [VariableComponent.Code]: {
    use: ModelCodesEditorButton,
    label: 'Code - 代码编辑器',
    type: CODE,
    allowTypeList: [CODE],
    displayType: CODE,
  },
  [VariableComponent.JSON]: {
    use: YAMLTemplateEditorButton,
    label: 'JSON - JSON编辑器',
    type: OBJECT,
    allowTypeList: [OBJECT],
    displayType: STRING,
    props: {
      language: 'json',
    },
  },
  [VariableComponent.DatasetPath]: {
    use: DatasetPathSelect,
    label: 'DatasetPath - 原始数据集路径选择器',
    type: STRING,
    allowTypeList: [STRING],
    displayType: STRING,
    props: {
      lazyLoad: {
        enable: true,
        page_size: 10,
      },
    },
  },
  [VariableComponent.FeatureSelect]: {
    use: Input,
    label: 'FeatureSelect - 特征选择器',
    type: OBJECT,
    allowTypeList: [OBJECT],
    displayType: STRING,
  },
  [VariableComponent.EnvsInput]: {
    use: EnvsInputForm,
    label: 'EnvsInput - 环境变量输入器',
    type: LIST,
    allowTypeList: [LIST],
    displayType: LIST,
  },
  [VariableComponent.AlgorithmSelect]: {
    use: AlgorithmSelect,
    label: 'AlgorithmSelect - 算法选择器',
    type: OBJECT,
    allowTypeList: [OBJECT],
    displayType: OBJECT,
  },
};

export const componentOptions = Object.entries(WIDGET_COMPONENTS__supported).map(([key, val]) => ({
  value: key,
  label: val.label,
}));

type Props = {
  form: any;
  path: (number | string)[];
  value?: VariableWidgetSchema;
  isCheck?: boolean;
  onChange?: (val: Variable) => any;
};

const WidgetSchema: FC<Props> = ({ form, path, value, isCheck }) => {
  const data = value;
  const variableIdx = path.slice(0, -1);

  const Widget = WIDGET_COMPONENTS__supported[data?.component!]?.use || Input;
  const widgetProps = WIDGET_COMPONENTS__supported[data?.component!]?.props || {};
  const allowTypeList: string[] =
    WIDGET_COMPONENTS__supported[data?.component!]?.allowTypeList ?? [];
  const defaultValueType: VariableValueType = WIDGET_COMPONENTS__supported[data?.component!]?.type;
  const displayType: VariableValueType =
    WIDGET_COMPONENTS__supported[data?.component!]?.displayType;
  const widgetHasEnum = _hasEnum(data?.component);
  const isCheckableCompnent = _isCheckableCompnent(data?.component);
  const isDisplayTypeSelect = _isDisplayTypeSelect(data?.component);

  const [valueType, setValueType] = useState<VariableValueType>(() => {
    // Get lastest valueType value from form
    const variables: Variable[] = form.getFieldValue('variables');
    return variables?.[variableIdx?.[0] as number]?.value_type ?? defaultValueType;
  });
  const tagList = [
    {
      label: '资源配置',
      value: Tag.RESOURCE_ALLOCATION,
    },
    {
      label: '输入参数',
      value: Tag.INPUT_PARAM,
    },
    {
      label: '输入路径',
      value: Tag.INPUT_PATH,
    },
    {
      label: '输出路径',
      value: Tag.OUTPUT_PATH,
    },
    {
      label: '运行参数',
      value: Tag.OPERATING_PARAM,
    },
    {
      label: '系统变量',
      value: Tag.SYSTEM_PARAM,
    },
  ];

  const formatValue = useCallback(
    (value: any) => {
      if (valueType === CODE) {
        return value;
      }

      if (displayType === VariableValueType.STRING) {
        if ((valueType === LIST || valueType === OBJECT) && typeof value === 'object') {
          return formatValueToString(value, valueType);
        }

        if (typeof value === 'string') {
          return value;
        }

        // Due to server only accept string type value
        if (typeof value === 'number') {
          return value.toString();
        }
      }

      if (
        [VariableValueType.CODE, VariableValueType.LIST, VariableValueType.OBJECT].includes(
          displayType,
        )
      ) {
        if (typeof value !== 'object') {
          try {
            const finalValue = JSON.parse(value);
            return finalValue;
          } catch (error) {
            // Do nothing
          }
        }
      }

      return value;
    },
    [valueType, displayType],
  );
  if (!data) return null;

  return (
    <div>
      <Form.Item
        field={[...path, 'component'].join('.')}
        label="请选择组件"
        rules={[{ required: true, message: '请选择组件' }]}
      >
        <Select disabled={isCheck} placeholder="请选择组件" onChange={onComponentChange}>
          {componentOptions.map((comp) => {
            return (
              <Select.Option key={comp.value} value={comp.value}>
                {comp.label}
              </Select.Option>
            );
          })}
        </Select>
      </Form.Item>

      <Form.Item
        field={[...variableIdx, 'value_type'].join('.')}
        label="值类型"
        hidden={!isDisplayTypeSelect}
      >
        <Select disabled={isCheck} placeholder="请选择值类型" onChange={onTypeChange}>
          {allowTypeList.map((type) => {
            return (
              <Select.Option key={type} value={type}>
                {type}
              </Select.Option>
            );
          })}
        </Select>
      </Form.Item>

      {widgetHasEnum && (
        <Form.Item
          field={[...path, 'enum'].join('.')}
          label="可选项"
          rules={[{ required: true, message: '请添加至少一个选项' }]}
        >
          <Form.List field={[...path, 'enum'].join('.')}>
            {(fields, { add, remove }) => {
              return (
                <div>
                  {fields.map((field, index) => {
                    return (
                      <div className={styled.enum} key={field.key + index}>
                        <Form.Item rules={[{ required: true, message: '填写选项值' }]} {...field}>
                          <Input disabled={isCheck} placeholder={`选项 ${index + 1}`} />
                        </Form.Item>
                        <IconButton
                          className={styled.del_enum_button}
                          disabled={isCheck}
                          circle
                          icon={<Delete />}
                          onClick={() => remove(field.key)}
                        />
                      </div>
                    );
                  })}

                  <Button
                    disabled={isCheck}
                    size="small"
                    icon={<PlusCircle />}
                    onClick={() => add()}
                  >
                    添加选项
                  </Button>
                </div>
              );
            }}
          </Form.List>
        </Form.Item>
      )}

      {/* The default value path is outside `widget_schema`, so the temp solution is name.slice(0, -1)  */}
      <Form.Item
        field={[...variableIdx, 'value'].join('.')}
        label="默认值"
        triggerPropName={isCheckableCompnent ? 'checked' : 'value'}
        normalize={formatValue}
        formatter={(val) => {
          let finalValue = val;
          // Because some value were be parsed as object by parseComplexDictField function, but it is has conflicts with displayType
          if (displayType === VariableValueType.STRING && typeof val === 'object') {
            finalValue = JSON.stringify(val);
          }
          return finalValue;
        }}
        rules={
          !widgetHasEnum &&
          (data?.component === VariableComponent.Input ||
            data?.component === VariableComponent.FeatureSelect) &&
          (valueType === LIST || valueType === OBJECT)
            ? [
                {
                  validator: (value: any, callback: (error?: string) => void) => {
                    // Hack: I don't know why value will be object type when I already set getValueProps function to format value to string type
                    // This situation happen when first render
                    if (typeof value === 'object') {
                      return;
                    }

                    try {
                      JSON.parse(value);
                      return;
                    } catch (error) {
                      callback(`JSON ${valueType} 格式错误`);
                    }
                  },
                },
              ]
            : []
        }
      >
        {widgetHasEnum ? (
          <Widget disabled={isCheck} placeholder="按需设置变量默认值" allowClear>
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
          <Widget
            disabled={isCheck}
            placeholder="按需设置变量默认值"
            allowClear
            path={[...variableIdx, 'value']}
            {...widgetProps}
          />
        )}
      </Form.Item>

      <Form.Item field={[...path, 'tooltip'].join('.')} label="用户输入提示">
        <Input disabled={isCheck} placeholder="输入提示解释该字段作用" />
      </Form.Item>

      <Form.Item field={[...path, 'tag'].join('.')} label="参数类型">
        <Select disabled={isCheck} placeholder="请选择参数类型" onChange={onTagChange}>
          {tagList.map((item) => {
            return (
              <Select.Option key={item.value} value={item.value}>
                {item.label}
              </Select.Option>
            );
          })}
        </Select>
      </Form.Item>

      <Form.Item field={[...path, 'required'].join('.')} triggerPropName="checked" label="是否必填">
        <Switch disabled={isCheck} />
      </Form.Item>
      <Form.Item field={[...path, 'hidden'].join('.')} triggerPropName="checked" label="是否隐藏">
        <Switch disabled={isCheck} />
      </Form.Item>
    </div>
  );

  function onTypeChange(type: VariableValueType) {
    setValueType(type);

    const result = { variables: form.getFieldValue('variables') };
    set(result, `[${variableIdx[0]}].value_type`, type);
    form.setFieldsValue(result);
  }

  function onTagChange(tag: string) {
    const result = { variables: form.getFieldValue('variables') };
    set(result, `[${variableIdx[0]}].tag`, tag);
    form.setFieldsValue(result);
  }

  function onComponentChange(val: VariableComponent) {
    setValueType(WIDGET_COMPONENTS__supported[val].type);

    const variables = form.getFieldValue('variables');

    const valueType = WIDGET_COMPONENTS__supported[val].type;

    const displayType: VariableValueType = WIDGET_COMPONENTS__supported[val]?.displayType;

    let defaultValue: any;

    // TODO: it's not clean to setFieldsValue using lodash-set, find a better way!
    set(variables, `[${variableIdx[0]}].value_type`, valueType);

    if (disabeldPeerWritableComponentTypeList.includes(val)) {
      set(variables, `[${variableIdx[0]}].access_mode`, VariableAccessMode.PEER_READABLE);
    }

    let isChangeValue = false;

    // Set '{}' as the default value of Code componets.
    if ([CODE, OBJECT].includes(valueType)) {
      defaultValue = {};
      if (val === VariableComponent.AlgorithmSelect) {
        defaultValue = { path: '', config: [] };
      }

      set(
        variables,
        `[${variableIdx[0]}].value`,
        displayType === VariableValueType.STRING ? JSON.stringify(defaultValue) : defaultValue,
      );
      isChangeValue = true;
    }
    if (valueType === LIST) {
      defaultValue = [];
      set(
        variables,
        `[${variableIdx[0]}].value`,
        displayType === VariableValueType.STRING ? JSON.stringify(defaultValue) : defaultValue,
      );
      isChangeValue = true;
    }
    /**
     * Remove enum value if component is not select/checkbox/radio etc.
     * cause formily will always render a select if enum is Array type in spite of
     * componet type is 'Input'
     */
    if (val !== VariableComponent.Select) {
      set(variables, `[${variableIdx[0]}].widget_schema.enum`, undefined);
    }

    if (val === VariableComponent.CPU) {
      set(variables, `[${variableIdx[0]}].value`, '1000m');
      isChangeValue = true;
    }

    if (val === VariableComponent.MEM) {
      set(variables, `[${variableIdx[0]}].value`, '1Gi');
      isChangeValue = true;
    }

    if (!isChangeValue) {
      set(variables, `[${variableIdx[0]}].value`, undefined);
    }

    form.setFieldsValue({
      variables,
    });
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
function _isDisplayTypeSelect(comp?: VariableComponent) {
  if (!comp) return false;
  const { Input } = VariableComponent;
  return [Input].includes(comp);
}

export default WidgetSchema;
