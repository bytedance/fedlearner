export type VariableComponent =
  | 'Input'
  | 'Select'
  | 'Radio'
  | 'Checkbox'
  | 'TextArea'
  | 'NumberPicker'
  | 'Switch'
  | 'TimePicker'
  | 'Upload'
  | 'Rating'

// TODO: Rules design: the simplest way is give a regexp
// but still need a path to access advanced validation like function
export type VariableRule = { validator: RegExp | string; message: string }

export interface VariableSchema {
  // key name in data
  key: string
  // i18n key for job name form-item label
  title: string
  // value type
  // NOTE: for array type value, it maybe a Multiple-Select
  // or a group item that allow user add | delete. eg. ENV field
  type: 'string' | 'numebr' | 'boolean' | 'array' | 'object'
  initialValue?: string | number | boolean | any[] | object
  // which component to use
  component: VariableComponent
  required?: boolean
  // static options for components like select | checkbox group | radio group...
  options?: Array<string | number | { value: any; label: string }>
  // same as above but the value is an endpoint of source
  dynamicOptions?: string
  componentProps: {
    [key: string]: any
  }
  rules?: VariableRule[]
  // will render a question icon beside the label, hover it to show the tooltip
  // for custom tooltip: { title: 'Tooltip with customize icon', icon: 'InfoCircleOutlined' }
  tooltip?: string
  // will render some text below the input
  description?: string
}
