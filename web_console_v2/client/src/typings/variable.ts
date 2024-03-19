/**
 * Widget schemas
 */
export interface InputWidgetSchema {
  /** ------ UIs ------ */
  prefix?: string;
  suffix?: string;
  showCount?: boolean;
  maxLength?: number;
}

export interface NumberPickerWidgetSchema {
  /** ------ UIs ------ */
  max?: number;
  min?: number;
  formatter?: (v: number) => string;
  parser?: (s: string) => number;
}

export interface TextAreaWidgetSchema {
  /** ------ UIs ------ */
  showCount?: boolean;
  maxLength?: number;
  rows?: number;
}

export interface SelectWidgetSchema {
  /** ------ Datas ------ */
  multiple?: boolean;
  filterable?: boolean;
}

export interface WidgetWithEnumSchema {
  /** ------ Datas ------ */
  enum?: any[];
}
export interface SwitchWidgetSchema {
  /** ------ uIs ------ */
  checkedChildren?: string;
  unCheckedChildren?: string;
}

/**
 * ! @IMPORTANT:
 * If you want to add new componet,
 * remember to add a worker in formSchema.tsx > componentToWorkersMap
 */
export enum VariableComponent {
  Input = 'Input',
  Select = 'Select',
  Radio = 'Radio',
  Checkbox = 'Checkbox',
  TextArea = 'TextArea',
  NumberPicker = 'NumberPicker',
  CPU = 'CPU',
  MEM = 'MEM',
  Switch = 'Switch',
  // -------- Custom components ----------
  Code = 'Code',
  JSON = 'JSON',
  Dataset = 'Dataset',
  DatasetPath = 'DatasetPath',
  FeatureSelect = 'FeatureSelect',
  EnvsInput = 'EnvsInput',
  AlgorithmSelect = 'AlgorithmSelect',
  // ------- Custom components ----------
  // Uncomment it after we have usecase
  // TimePicker = 'TimePicker',
  // Upload = 'Upload',
}

export interface VariableWidgetSchema
  extends NumberPickerWidgetSchema,
    TextAreaWidgetSchema,
    SwitchWidgetSchema,
    SelectWidgetSchema,
    InputWidgetSchema,
    WidgetWithEnumSchema {
  /** ------ Metas ------ */
  // which component to use
  component?: VariableComponent;

  /** ------ UIs ------ */
  // i18n key for job name form-item label
  label?: string;
  // display order
  index?: number;
  // will render a question icon beside the label, hover it to show the tooltip
  tooltip?: string;
  // control variables' visibility, will not affect value
  hidden?: boolean;
  // will render some text below the form item
  description?: string;
  placeholder?: string;

  /** ------ Validations ------ */
  // RegExp string '\d'
  pattern?: any;
  rules?: any[];
  required?: boolean;

  /** ------ Miscs ------ */
  [key: string]: any;
}

export enum VariableAccessMode {
  UNSPECIFIED = 'UNSPECIFIED',
  PRIVATE = 'PRIVATE',
  PEER_READABLE = 'PEER_READABLE',
  PEER_WRITABLE = 'PEER_WRITABLE',
}

export enum VariableValueType {
  STRING = 'STRING',
  CODE = 'CODE',
  BOOLEAN = 'BOOLEAN',
  NUMBER = 'NUMBER',
  LIST = 'LIST',
  OBJECT = 'OBJECT',
}

export interface Variable {
  name: string;
  // Due to proto doesn't has more optional types, we fixed to use string as value type,
  // for boolean/number value, should convert to 'true', '2' directly (but so far, we don't need values like boolean)
  value: any;
  tag?: string;
  typed_value?: any;
  value_type?: VariableValueType;
  access_mode: VariableAccessMode;
  widget_schema: VariableWidgetSchema;
}
