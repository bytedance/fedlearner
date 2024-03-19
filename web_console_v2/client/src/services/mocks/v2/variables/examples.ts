import {
  Variable,
  VariableAccessMode,
  VariableComponent,
  VariableValueType,
} from 'typings/variable';
import { Tag } from 'typings/workflow';

export const unassignedComponent: Variable = {
  name: 'component_unassigned',
  value: '',
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {},
};

export const nameInput: Variable = {
  tag: Tag.INPUT_PATH,
  name: 'some_name',
  value: 'initial value',
  typed_value: 'initial value',
  value_type: VariableValueType.STRING,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
  },
};

export const memSelect: Variable = {
  tag: Tag.INPUT_PATH,
  name: 'worker_mem',
  value: 2,
  typed_value: 2,
  value_type: VariableValueType.NUMBER,
  access_mode: VariableAccessMode.PRIVATE,
  widget_schema: {
    component: VariableComponent.Select,
    type: 'number',
    required: true,
    enum: [
      { value: 1, label: '1Gi' },
      { value: 2, label: '2Gi' },
    ],
    placeholder: '请选择内存',
  },
};

export const asyncSwitch: Variable = {
  tag: Tag.OPERATING_PARAM,
  name: 'is_async',
  value: false,
  typed_value: false,
  value_type: VariableValueType.BOOLEAN,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.Switch,
    label: '是否异步',
    type: 'boolean',
    checkedChildren: 'Async mode',
    unCheckedChildren: 'Synchronous mode',
  },
};

export const cpuLimit: Variable = {
  tag: Tag.OPERATING_PARAM,
  name: 'cpu_limit',
  value: 2,
  typed_value: 2,
  value_type: VariableValueType.NUMBER,
  access_mode: VariableAccessMode.PRIVATE,
  widget_schema: {
    component: VariableComponent.NumberPicker,
    type: 'number',
    min: 10,
    max: 100,
  },
};

export const commentTextArea: Variable = {
  tag: Tag.RESOURCE_ALLOCATION,
  name: 'comment',
  value: '',
  typed_value: '',
  value_type: VariableValueType.STRING,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.TextArea,
    type: 'string',
    rows: 6,
    showCount: true,
    placeholder: '备注',
  },
};

export const gloabalVariables: Variable[] = [
  {
    tag: Tag.RESOURCE_ALLOCATION,
    name: 'image_version',
    value: 'v1.5-rc3',
    typed_value: 'v1.5-rc3',
    value_type: VariableValueType.STRING,
    access_mode: VariableAccessMode.PEER_READABLE,
    widget_schema: {
      required: true,
    },
  },
  {
    tag: Tag.RESOURCE_ALLOCATION,
    name: 'num_partitions',
    value: '4',
    typed_value: 'v1.5-rc3',
    value_type: VariableValueType.STRING,
    access_mode: VariableAccessMode.PEER_READABLE,
    widget_schema: '' as any,
  },
  {
    tag: Tag.RESOURCE_ALLOCATION,
    name: 'worker_cpu',
    value: 1,
    value_type: VariableValueType.NUMBER,
    access_mode: VariableAccessMode.PRIVATE,
    widget_schema: {
      component: VariableComponent.Select,
      type: 'number',
      required: true,
      enum: [
        { value: 1, label: '1Gi' },
        { value: 2, label: '2Gi' },
      ],
    },
  },
];

export const codeEditor: Variable = {
  tag: Tag.INPUT_PATH,
  name: 'code_tar',
  value: { 'main.js': 'var a = 1;' },
  typed_value: { 'main.js': 'var a = 1;' },
  value_type: VariableValueType.CODE,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.Code,
    placeholder: '代码',
  },
};

export const datasetSelect: Variable = {
  name: 'dataset',
  value: '',
  typed_value: '',
  value_type: VariableValueType.STRING,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.Dataset,
    placeholder: '数据集',
  },
};

export const datasetPathSelect: Variable = {
  name: 'dataset_path',
  value: '',
  typed_value: '',
  value_type: VariableValueType.STRING,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.DatasetPath,
    placeholder: '数据集路径',
  },
};
export const featureSelect: Variable = {
  name: 'feature',
  value: {},
  typed_value: {},
  value_type: VariableValueType.OBJECT,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.FeatureSelect,
    placeholder: '特征选择器',
  },
};

export const envsInput: Variable = {
  name: 'kv_list',
  value: [
    { key: 'key1', value: 'value1' },
    { key: 'key2', value: 'value2' },
  ],
  typed_value: [
    { name: 'n1', value: 'v1' },
    { name: 'n2', value: 'v2' },
  ],
  value_type: VariableValueType.LIST,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.EnvsInput,
    placeholder: 'envsInput',
  },
};

export const stringInput: Variable = {
  name: 'string_input',
  value: 'initial value',
  typed_value: 'initial value',
  value_type: VariableValueType.STRING,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
    required: true,
  },
};
export const numberInput: Variable = {
  tag: Tag.OPERATING_PARAM,
  name: 'number_input',
  value: '1',
  typed_value: 1,
  value_type: VariableValueType.NUMBER,
  access_mode: VariableAccessMode.PEER_WRITABLE,
  widget_schema: {
    component: VariableComponent.NumberPicker,
    type: 'number',
    min: 1,
    max: 100,
  },
};

export const objectInput: Variable = {
  tag: Tag.INPUT_PATH,
  name: 'object_input',
  value: JSON.stringify({ a: 1 }),
  typed_value: { a: 1 },
  value_type: VariableValueType.OBJECT,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
  },
};
export const listInput: Variable = {
  tag: Tag.SYSTEM_PARAM,
  name: 'list_input',
  value: JSON.stringify([{ a: 1 }]),
  typed_value: [{ a: 1 }],
  value_type: VariableValueType.LIST,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
  },
};
export const forceObjectInput: Variable = {
  name: 'force_object_input',
  value: { a: 1 },
  typed_value: { a: 1 },
  value_type: VariableValueType.OBJECT,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
  },
};
export const forceListInput: Variable = {
  name: 'force_list_input',
  value: [{ a: 1 }],
  typed_value: [{ a: 1 }],
  value_type: VariableValueType.LIST,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
  },
};

export const hideStringInput: Variable = {
  tag: Tag.INPUT_PATH,
  name: 'hide_string_input',
  value: 'initial value',
  typed_value: 'initial value',
  value_type: VariableValueType.STRING,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
    hidden: true,
  },
};
