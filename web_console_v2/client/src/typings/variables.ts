export enum VariableComponent {
  Input = 'Input',
  Select = 'Select',
  Radio = 'Radio',
  Checkbox = 'Checkbox',
  TextArea = 'TextArea',
  NumberPicker = 'NumberPicker',
  Switch = 'Switch',
  TimePicker = 'TimePicker',
  Upload = 'Upload',
}

// TODO: Rules design: the simplest way is give a regexp
// but still need a path to access advanced validation like function
export type VariableRule = { validator: RegExp | string; message: string }

interface InputWidgetSchema {
  /** ------ UIs ------ */
  prefix?: string
  suffix?: string
  showCount?: boolean
  maxLength?: number
}

interface NumberPickerWidgetSchema {
  /** ------ UIs ------ */
  max?: number
  min?: number
  formatter?: (v: number) => string
  parser?: (s: string) => number
}

interface TextAreaWidgetSchema {
  /** ------ UIs ------ */
  showCount?: boolean
  maxLength?: number
  rows?: number
}

interface SelectWidgetSchema {
  /** ------ Datas ------ */
  multiple?: boolean
  filterable?: boolean
}

interface WidgetWithOptionsSchema {
  /** ------ Datas ------ */
  options?: {
    type: 'static' | 'dynamic'
    // 1. static options for components like select | checkbox group | radio group...
    // 2. dynamic options is an endpoint of source
    source: Array<string | number | { value: any; label: string }> | string
  }
}
interface SwitchWidgetSchema {
  /** ------ uIs ------ */
  checkedChildren?: string
  unCheckedChildren?: string
}

interface UploadWidgetSchema {
  /** ------ Datas ------ */
  accept?: string
  action?: string
  multiple?: boolean
}
export interface VariableWidgetSchema
  extends UploadWidgetSchema,
    SelectWidgetSchema,
    NumberPickerWidgetSchema,
    TextAreaWidgetSchema,
    SwitchWidgetSchema,
    SelectWidgetSchema,
    InputWidgetSchema,
    WidgetWithOptionsSchema {
  /** ------ Metas ------ */
  // which component to use
  component: VariableComponent

  /** ------ Datas ------ */
  // NOTE: for array type value, it clould be either a Multiple-select/Checkbox
  // or a Group-items which allow user add | delete. eg. ENV field
  type: 'string' | 'numebr' | 'boolean' | 'array' | 'object'
  initialValue?: string | number | boolean | any[] | object

  /** ------ UIs ------ */
  // i18n key for job name form-item label
  label: string
  // display order
  index: number
  // will render a question icon beside the label, hover it to show the tooltip
  tooltip?: string
  // will render some text below the form item
  description?: string
  placeholder?: string
  size?: ComponentSize

  /** ------ Validations ------ */
  // RegExp string '\d'
  pattern?: string
  rules?: VariableRule[]

  /** ------ Miscs ------ */
  [key: string]: any
}

export enum VariableAccessMode {
  UNSPECIFIED,
  PRIVATE,
  PEER_READABLE,
  PEER_WRITABLE,
}

export interface Variable {
  name: string
  value: any
  access_mode: VariableAccessMode
  widget_schema: VariableWidgetSchema
}
