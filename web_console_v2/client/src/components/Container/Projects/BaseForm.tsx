import React, { ReactElement } from 'react'
import styled from "styled-components"
import { Form, Input } from 'antd'
import { useTranslation } from 'react-i18next'

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

  > .ant-form-item{
    &:last-child{
      margin-bottom: 0;
    }
  }
`

const layout = {
  labelCol: { span: 8 },
  wrapperCol: { span: 13 },
};

function BaseForm(): ReactElement {
  const { t } = useTranslation()
  return (
    <BaseFormStyle {...layout}>
      <Form.Item
        name="projectname"
        label={t('project_name')}
        rules={[{ required: true, message: '项目名称', }]}
      >
        <Input name="projectname" placeholder={t('project_name_placeholder')} />
      </Form.Item>
      <Form.Item
        name="partnername"
        label={t('project_partner_name')}
        rules={[{ required: true, message: '合作伙伴名称', }]}
      >
        <Input name="partnername" placeholder={t('project_partner_name_placeholder')} />
      </Form.Item>
      <Form.Item
        name="parterpoint"
        label={t('project_partner_url')}
        rules={[{ required: true, message: '合作伙伴节点地址', }]}
      >
        <Input name="parterpoint" placeholder={t('project_partner_url_placeholder')} />
      </Form.Item>
      <Form.Item
        name="remark"
        label={t('project_remarks')}
      >
        <Input.TextArea rows={4} style={{resize: "none"}} name="remark" placeholder={t('project_remarks_placeholder')} />
      </Form.Item>
    </BaseFormStyle>
  )
}

export default BaseForm
