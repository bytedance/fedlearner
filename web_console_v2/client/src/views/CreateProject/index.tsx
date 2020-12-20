import React, { ReactElement } from 'react'
import BaseForm from './BaseForm'
import styled from 'styled-components'
import { Form } from 'antd'
import Breadcrumb from 'components/Container/Breadcrumb'

const Container = styled.div``
// async function createProject() {
//   try {
//     const val = await form.validateFields()
//     console.log(val)
//   } catch (error) {
//     console.log(error)
//   }
// }

function CreateProject(): ReactElement {
  const [form] = Form.useForm()
  return (
    <Container>
      <Breadcrumb />
      <BaseForm form={form} />
    </Container>
  )
}

export default CreateProject
