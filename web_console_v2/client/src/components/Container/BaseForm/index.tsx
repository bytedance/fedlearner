import React, { ReactElement, useState } from 'react'
import styled from 'styled-components'
import { Form, Input, Button, Radio, Upload } from 'antd'
import { useTranslation } from 'react-i18next'
import SecondaryForm from './SecondaryForm'
import EnvPathsForm from './EnvPathsForm'
import FileUploaded from '../FileUploaded'
import UploadArea from '../UploadArea'
import { CertificateConfigType } from 'typings/enum'

const Container = styled.div`
  padding: 16px;
  width: 100%;
`

const BaseFormStyle = styled(Form)`
  width: 100%;
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

const FileFormItem = styled(Form.Item)`
  flex-wrap: nowrap;
  .ant-upload {
    background: var(--gray2);
    border-radius: 2px;
    border: none;
  }
`

const layout = {
  labelCol: { span: 8 },
  wrapperCol: { span: 20 },
}

interface Props {
  onSubmit: <T>(payload: T) => void
  edit?: boolean
  initialValues?: FormInitialValues
}

const SubmitContainer = styled(Form.Item)`
  background-color: white;
  padding: 24px;
  margin-top: 14px;
  border-radius: 4px;
  width: 100%;
  .cancel-button {
    margin-left: 16px;
  }
`

const defaultInitialValues: FormInitialValues = {
  certificateConfigType: CertificateConfigType.Upload,
  name: '',
  participantName: '',
  participantUrl: '',
  participantDomainName: '',
  comment: '',
  variables: [],
}

function BaseForm({ onSubmit, edit, initialValues }: Props): ReactElement {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [certificates, setCertificates] = useState('')
  const [certificatesName, setCertificatesName] = useState('')
  const [certificatesUploading, setCertificatesUploading] = useState(false)

  const defaultValues: FormInitialValues = initialValues ?? defaultInitialValues
  const [certificateConfigType, setCertificateConfigType] = useState(
    defaultValues.certificateConfigType,
  )
  return (
    <Container>
      <BaseFormStyle {...layout} initialValues={defaultValues} form={form} colon={false}>
        <SecondaryForm title={t('project.basic_information')}>
          <Form.Item
            name="name"
            label={t('project.name')}
            rules={[{ required: true, message: t('project.name_message') }]}
          >
            <Input name="name" placeholder={t('project.name_placeholder')} disabled={edit} />
          </Form.Item>
        </SecondaryForm>
        <SecondaryForm title={t('project.participant_information')} suffix={<EnvPathsForm />}>
          <Form.Item
            name="participantName"
            label={t('project.participant_name')}
            rules={[{ required: true, message: t('project.participant_name_message') }]}
          >
            <Input
              name="participantName"
              placeholder={t('project.participant_name_placeholder')}
              disabled={edit}
            />
          </Form.Item>
          <Form.Item
            name="participantUrl"
            label={t('project.participant_url')}
            rules={[{ required: true, message: t('project.participant_url_message') }]}
          >
            <Input
              name="participantUrl"
              placeholder={t('project.participant_url_placeholder')}
              disabled={edit}
            />
          </Form.Item>
          <Form.Item
            name="certificateConfigType"
            label={t('certificate')}
            rules={[{ required: true }]}
          >
            <Radio.Group
              options={[
                {
                  label: t('project.upload_certificate'),
                  value: 1,
                },
                {
                  label: t('project.backend_config_certificate'),
                  value: 2,
                },
              ]}
              optionType="button"
              onChange={(e) => {
                setCertificateConfigType(e.target.value)
              }}
              disabled={edit}
            />
          </Form.Item>
          {certificateConfigType === CertificateConfigType.Upload ? (
            <FileFormItem label name="upload">
              {certificates ? (
                <FileUploaded
                  onDelete={handelFileDelete}
                  fileName={certificatesName}
                  loading={certificatesUploading}
                />
              ) : (
                <Upload.Dragger disabled={edit} beforeUpload={onUpload} accept=".gz">
                  <UploadArea suffix={t('project.upload_certificate_placeholder')} />
                </Upload.Dragger>
              )}
            </FileFormItem>
          ) : null}
          <Form.Item
            name="participantDomainName"
            label={t('project.participant_domain')}
            rules={[{ required: true, message: t('project.participant_domain_message') }]}
          >
            <Input
              name="participantDomainName"
              placeholder={t('project.participant_domain_placeholder')}
              disabled={edit}
            />
          </Form.Item>
          <Form.Item name="comment" label={t('project.remarks')}>
            <Input.TextArea
              rows={4}
              style={{ resize: 'none' }}
              name="comment"
              placeholder={t('project.remarks_placeholder')}
            />
          </Form.Item>
        </SecondaryForm>
        <SubmitContainer>
          <Button type="primary" onClick={handleSubmit}>
            {t('submit')}
          </Button>
          <Button className="cancel-button">{t('cancel')}</Button>
        </SubmitContainer>
      </BaseFormStyle>
    </Container>
  )
  async function handleSubmit() {
    if (!edit && certificateConfigType === CertificateConfigType.Upload && certificates === '') {
      form.setFields([{ name: 'upload', errors: [t('project.upload_certificate_message')] }])
      form.scrollToField('certificateConfigType', { block: 'center' })
      return
    }
    try {
      const data = await form.validateFields()
      let params: CreateProjectFormData | UpdateProjectFormData
      if (edit) {
        params = {
          variables: data.variables ?? [],
          comment: data.comment,
        }
        onSubmit(params)
      } else {
        let participants: Participant[] = []
        participants.push({
          name: data.participantName,
          url: data.participantUrl,
          domain_name: data.participantDomainName,
          certificates:
            certificateConfigType === CertificateConfigType.Upload ? certificates : null,
        })
        params = {
          name: data.name,
          config: {
            participants,
            variables: data.variables ?? [],
          },
          comment: data.comment,
        }
        onSubmit(params)
      }
    } catch (error) {
      form.scrollToField(error.errorFields[0].name[0], { block: 'center' })
    }
  }
  function onUpload(file: File) {
    if (file.size > 20 * 1024 * 1024) {
      form.setFields([{ name: 'upload', errors: [t('project.upload_certificate_placeholder')] }])
      return false
    }
    var reader = new FileReader()
    setCertificatesName(file.name)
    setCertificatesUploading(true)
    reader.onload = function (e) {
      if (typeof reader.result === 'string') {
        setCertificates(btoa(reader.result))
        form.setFields([{ name: 'upload', errors: [] }])
      }
      setCertificatesUploading(false)
    }
    reader.readAsBinaryString(file)
    return false
  }
  function handelFileDelete() {
    setCertificates('')
    setCertificatesName('')
  }
}

export default BaseForm
