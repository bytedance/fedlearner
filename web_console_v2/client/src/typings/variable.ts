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

export interface WidgetWithOptionsSchema {
  /** ------ Datas ------ */
  options?: {
    type: 'static' | 'dynamic';
    // 1. static options for components like select | checkbox group | radio group...
    // 2. dynamic options is an endpoint of source
    source: Array<string | number | { value: any; label: string }> | string;
  };
}
export interface SwitchWidgetSchema {
  /** ------ uIs ------ */
  checkedChildren?: string;
  unCheckedChildren?: string;
}

export enum VariableComponent {
  Input = 'Input',
  Select = 'Select',
  Radio = 'Radio',
  Checkbox = 'Checkbox',
  TextArea = 'TextArea',
  NumberPicker = 'NumberPicker',
  Switch = 'Switch',
  Code = 'Code',
  // Uncomment it after we have usecase
  // TimePicker = 'TimePicker',
  // Upload = 'Upload',
}

export type VariableRule = { validator: RegExp | string; message: string };

export interface VariableWidgetSchema
  extends SelectWidgetSchema,
    NumberPickerWidgetSchema,
    TextAreaWidgetSchema,
    SwitchWidgetSchema,
    SelectWidgetSchema,
    InputWidgetSchema,
    WidgetWithOptionsSchema {
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
  // will render some text below the form item
  description?: string;
  placeholder?: string;

  /** ------ Validations ------ */
  // RegExp string '\d'
  pattern?: string;
  rules?: VariableRule[];
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
}

export interface Variable {
  name: string;
  // Due to proto doesn't has more optional types, we fixed to use string as value type,
  // for boolean/number value, should convert to 'true', '2' directly (but so far, we don't need values like boolean)
  value: any;
  type?: VariableValueType;
  access_mode: VariableAccessMode;
  widget_schema: VariableWidgetSchema;
}
