import React from 'react'
import styled from 'styled-components'
import { Row, Card, Form, Select, Radio, Button, Upload, Input, Col } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import GridRow from 'components/_base/GridRow'

const { Option } = Select

const BasicInfoForm = styled(Form)`
  width: 500px;
`

const normFile = (e: any) => {
  console.log('Upload event:', e)
  if (Array.isArray(e)) {
    return e
  }
  return e && e.fileList
}

function WorkflowsCreateStepOne() {
  const { t } = useTranslation()
  const onFinish = (values: any) => {
    console.log('Received values of form: ', values)
  }

  return (
    <Card>
      <Row justify="center">
        <BasicInfoForm
          labelCol={{ span: 6 }}
          wrapperCol={{ span: 18 }}
          onFinish={onFinish}
          initialValues={{
            _templateType: 'new',
            peer_forkable: true,
          }}
        >
          <Form.Item
            name="name"
            hasFeedback
            label={t('workflows.label_name')}
            rules={[{ required: true, message: 'Please select your favourite colors!' }]}
          >
            <Input placeholder={t('workflows.placeholder_name')} />
          </Form.Item>

          <Form.Item
            name="projecto_token"
            label={t('workflows.label_project')}
            hasFeedback
            rules={[{ required: true, message: 'Please select your country!' }]}
          >
            <Select placeholder={t('workflows.placeholder_project')}>
              <Option value="china">China</Option>
              <Option value="usa">U.S.A</Option>
            </Select>
          </Form.Item>

          <Form.Item name="peer_forkable" label={t('workflows.label_peer_forkable')}>
            <Radio.Group>
              <Radio value={true}>{t('workflows.label_allow')}</Radio>
              <Radio value={false}>{t('workflows.label_not_allow')}</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item name="_templateType" label={t('workflows.label_template')}>
            <Radio.Group>
              <Radio.Button value={'new'}>{t('workflows.label_exist_template')}</Radio.Button>
              <Radio.Button value={'create'}>{t('workflows.label_new_template')}</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item wrapperCol={{ offset: 6 }}>
            <Form.Item name="dragger" valuePropName="fileList" getValueFromEvent={normFile} noStyle>
              <Upload.Dragger name="files" action="/upload.do">
                <p className="ant-upload-drag-icon">
                  <PlusOutlined />
                </p>
                <p className="ant-upload-text">{t('upload.placeholder')}</p>
                <p className="ant-upload-hint">{t('upload.hint')}</p>
              </Upload.Dragger>
            </Form.Item>
          </Form.Item>

          <Form.Item wrapperCol={{ offset: 6 }}>
            <GridRow gap={16}>
              <Button type="primary">{t('next_step')}</Button>

              <Button htmlType="submit">{t('cancel')}</Button>
            </GridRow>
          </Form.Item>
        </BasicInfoForm>
      </Row>
    </Card>
  )
}

export default WorkflowsCreateStepOne
