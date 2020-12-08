import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import { Form, Input, Space } from 'antd'
import { useTranslation } from 'react-i18next'
import AddField from './AddField'
import RemoveField from './RemoveField'

const Container = styled.div``

interface Props {}

interface EnvPath {
  name: string
  value: string
}

const formItemLayout = {
  labelCol: {
    xs: { span: 24 },
    sm: { span: 4 },
  },
  wrapperCol: {
    xs: { span: 24 },
    sm: { span: 20 },
  },
}
const formItemLayoutWithOutLabel = {
  wrapperCol: {
    xs: { span: 24, offset: 0 },
    sm: { span: 20, offset: 4 },
  },
}

function EnvPathsForm({}: Props): ReactElement {
  const { t } = useTranslation()
  return (
    <Container>
      <Form.List name="names">
        {(fields, { add, remove }, { errors }) => (
          <>
            {fields.map((field, index) => (
              <Space key={field.key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                <Form.Item
                  {...field}
                  label="Name"
                  name={[field.name, 'name']}
                  fieldKey={[field.fieldKey, 'name']}
                  rules={[{ required: true, message: 'Missing first name' }]}
                >
                  <Input placeholder="name" />
                </Form.Item>
                <Form.Item
                  label="Value"
                  {...field}
                  name={[field.name, 'value']}
                  fieldKey={[field.fieldKey, 'value']}
                >
                  <Input.TextArea placeholder="value" />
                </Form.Item>
                <RemoveField onClick={() => remove(field.name)} />
              </Space>
            ))}
            <Form.Item>
              <AddField onClick={() => add()} />
            </Form.Item>
          </>
        )}
      </Form.List>
    </Container>
  )
}

export default EnvPathsForm
