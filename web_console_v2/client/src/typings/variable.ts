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

  /** ------ Datas ------ */
  // NOTE: for array type value, it clould be either a Multiple-select/Checkbox
  // or a Group-items which allow user add | delete. eg. ENV field
  type?: 'string' | 'number' | 'boolean' | 'array' | 'object';

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

export interface Variable {
  name: string;
  value: any;
  access_mode: VariableAccessMode;
  widget_schema: VariableWidgetSchema;
}
