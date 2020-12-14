import React from 'react'
import { SchemaForm, FormButtonGroup, Submit } from '@formily/antd'
import {
  Input,
  NumberPicker,
  Select,
  Radio,
  Checkbox,
  Switch,
  Upload,
} from '@formily/antd-components'

const components = {
  Input,
  NumberPicker,
  Select,
  Radio,
  Checkbox,
  TextArea: Input.TextArea,
  Switch,
  Upload,
}

type Props = {
  schema: any
  onConfirm: (val: any) => void
}

function VariableSchemaForm({ schema, onConfirm }: Props) {
  return (
    <SchemaForm components={components} schema={schema} labelCol={4} onSubmit={onConfirm}>
      <FormButtonGroup>
        {/* FIXME: demo button here */}
        <Submit>Print</Submit>
      </FormButtonGroup>
    </SchemaForm>
  )
}

export default VariableSchemaForm
