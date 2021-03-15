import {
  Variable,
  VariableAccessMode,
  VariableComponent,
  VariableValueType,
} from 'typings/variable';

export const unassignedComponent: Variable = {
  name: 'component_unassigned',
  value: '',
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {},
};

export const nameInput: Variable = {
  name: 'some_name',
  value: 'initial value',
  variable_type: VariableValueType.STRING,
  access_mode: VariableAccessMode.PEER_READABLE,
  widget_schema: {
    component: VariableComponent.Input,
    tooltip: 'some hints',
  },
};

export const memSelect: Variable = {
  name: 'worker_mem',
  value: 2,
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
  name: 'is_async',
  value: false,
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
  name: 'cpu_limit',
  value: false,
  access_mode: VariableAccessMode.PRIVATE,
  widget_schema: {
    component: VariableComponent.NumberPicker,
    type: 'number',
    min: 10,
    max: 100,
  },
};

export const commentTextArea: Variable = {
  name: 'comment',
  value: '',
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
    name: 'image_version',
    value: 'v1.5-rc3',
    access_mode: VariableAccessMode.PEER_READABLE,
    widget_schema: {
      required: true,
    },
  },
  {
    name: 'num_partitions',
    value: '4',
    access_mode: VariableAccessMode.PEER_READABLE,
    widget_schema: '' as any,
  },
  {
    name: 'worker_cpu',
    value: 1,
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
