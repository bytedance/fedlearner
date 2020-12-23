export type ComponentSize = 'small' | 'medium' | 'large' | 'default'

export interface StyledComponetProps {
  className?: string
  [key: string]: any
}

/**
 * Widget schemas
 */
export interface InputWidgetSchema {
  /** ------ UIs ------ */
  prefix?: string
  suffix?: string
  showCount?: boolean
  maxLength?: number
}

export interface NumberPickerWidgetSchema {
  /** ------ UIs ------ */
  max?: number
  min?: number
  formatter?: (v: number) => string
  parser?: (s: string) => number
}

export interface TextAreaWidgetSchema {
  /** ------ UIs ------ */
  showCount?: boolean
  maxLength?: number
  rows?: number
}

export interface SelectWidgetSchema {
  /** ------ Datas ------ */
  multiple?: boolean
  filterable?: boolean
}

export interface WidgetWithOptionsSchema {
  /** ------ Datas ------ */
  options?: {
    type: 'static' | 'dynamic'
    // 1. static options for components like select | checkbox group | radio group...
    // 2. dynamic options is an endpoint of source
    source: Array<string | number | { value: any; label: string }> | string
  }
}
export interface SwitchWidgetSchema {
  /** ------ uIs ------ */
  checkedChildren?: string
  unCheckedChildren?: string
}

export interface UploadWidgetSchema {
  /** ------ Datas ------ */
  accept?: string
  action?: string
  multiple?: boolean
}
