import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Form, Input } from 'antd'
import { useTranslation } from 'react-i18next'
import SecondaryForm from './SecondaryForm'
import EnvPathsForm from './EnvPathsForm'

const BaseFormStyle = styled(Form)`
  width: 400px;

  > .form-title {
    margin-bottom: 24px;
    font-size: 27px;
    line-height: 36px;
  }

  > .ant-space {
    display: flex;
  }

  > .ant-form-item {
    &:last-child {
      margin-bottom: 0;
    }
  }
`

const layout = {
  labelCol: { span: 10 },
  wrapperCol: { span: 20 },
}

interface Props {
  form: any
}

function BaseForm({ form }: Props): ReactElement {
  const { t } = useTranslation()
  return (
    <BaseFormStyle {...layout} form={form}>
      <SecondaryForm title="基本信息">
        <Form.Item
          name="projectname"
          label={t('project_name')}
          rules={[{ required: true, message: t('project_name_message') }]}
        >
          <Input name="projectname" placeholder={t('project_name_placeholder')} />
        </Form.Item>
      </SecondaryForm>

      <SecondaryForm title="合作伙伴信息">
        <Form.Item
          name="partnername"
          label={t('project_partner_name')}
          rules={[{ required: true, message: t('project_partner_name_message') }]}
        >
          <Input name="partnername" placeholder={t('project_partner_name_placeholder')} />
        </Form.Item>
        <Form.Item
          name="parterpoint"
          label={t('project_partner_url')}
          rules={[{ required: true, message: t('project_partner_url_message') }]}
        >
          <Input name="parterpoint" placeholder={t('project_partner_url_placeholder')} />
        </Form.Item>
        <Form.Item
          name="genericdomain"
          label={'泛域名'}
          rules={[{ required: true, message: t('project_partner_url_message') }]}
        >
          <Input name="genericdomain" placeholder={t('project_partner_url_placeholder')} />
        </Form.Item>
        <Form.Item name="remark" label={t('project_remarks')}>
          <Input.TextArea
            rows={4}
            style={{ resize: 'none' }}
            name="remark"
            placeholder={t('project_remarks_placeholder')}
          />
        </Form.Item>
      </SecondaryForm>
      <SecondaryForm title="环境变量参数配置" folded>
        <EnvPathsForm />
      </SecondaryForm>
    </BaseFormStyle>
  )
}

export default BaseForm