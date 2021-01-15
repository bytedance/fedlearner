import React, { ReactElement, useState } from 'react';
import styled from 'styled-components';
import { Form, Input, Button, Radio, message, Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import SecondaryForm from './SecondaryForm';
import EnvVariablesForm from './EnvVariablesForm';
import { CertificateConfigType } from 'typings/project';
import {
  ProjectFormInitialValues,
  CreateProjectFormData,
  UpdateProjectFormData,
  Participant,
} from 'typings/project';
import { useHistory } from 'react-router-dom';
import ReadFile from 'components/ReadFile';
import { readAsBinaryStringFromFile } from 'shared/file';
import GridRow from 'components/_base/GridRow';
import i18n from 'i18n';

const Container = styled.div`
  flex: 1;
`;
const StyledForm = styled(Form)`
  display: grid;
  grid-auto-rows: auto 1fr auto;

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
`;
const FileFormItem = styled(Form.Item)`
  flex-wrap: nowrap;
`;

const layout = {
  labelCol: { span: 8 },
  wrapperCol: { span: 20 },
};

interface Props {
  onSubmit: <T>(payload: T) => void;
  edit?: boolean;
  initialValues?: ProjectFormInitialValues;
}

const SubmitContainer = styled(Form.Item)`
  background-color: white;
  padding: 24px;
  margin-top: 14px;
  border-radius: 4px;
  width: 100%;
`;

const defaultInitialValues: ProjectFormInitialValues = {
  certificateConfigType: CertificateConfigType.Upload,
  name: '',
  participantName: '',
  participantUrl: '',
  participantDomainName: '',
  comment: '',
  variables: [],
};

function BaseForm({ onSubmit, edit, initialValues }: Props): ReactElement {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const history = useHistory();

  const defaultValues: ProjectFormInitialValues = initialValues ?? defaultInitialValues;
  const [certificateConfigType, setCertificateConfigType] = useState(
    defaultValues.certificateConfigType,
  );
  return (
    <Container>
      <StyledForm
        {...layout}
        initialValues={defaultValues}
        form={form}
        colon={false}
        onFinish={onFinish}
      >
        <SecondaryForm title={t('project.basic_information')}>
          <Form.Item
            hasFeedback
            name="name"
            label={t('project.name')}
            rules={[{ required: true, message: t('project.name_message') }]}
          >
            <Input name="name" placeholder={t('project.name_placeholder')} disabled={edit} />
          </Form.Item>
        </SecondaryForm>
        <SecondaryForm title={t('project.participant_information')}>
          <Form.Item
            hasFeedback
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
            hasFeedback
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
                  value: 0,
                },
                {
                  label: t('project.backend_config_certificate'),
                  value: 1,
                },
              ]}
              optionType="button"
              onChange={(e) => {
                setCertificateConfigType(e.target.value);
              }}
              disabled={edit}
            />
          </Form.Item>

          {certificateConfigType === CertificateConfigType.Upload ? (
            <FileFormItem
              label
              name="certificate"
              rules={[{ required: true, message: t('project.upload_certificate_message') }]}
            >
              {/* TODO: read error info from form-item */}
              <ReadFile disabled={edit} accept=".gz" reader={readAsBinaryStringFromFile} />
            </FileFormItem>
          ) : null}

          <Form.Item
            hasFeedback
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

          <EnvVariablesForm />
        </SecondaryForm>

        <SubmitContainer>
          <GridRow gap="16">
            <Button type="primary" loading={loading} onClick={onSubmitClick}>
              {t('submit')}
            </Button>
            <Button onClick={onCancelClick}>{t('cancel')}</Button>
          </GridRow>
        </SubmitContainer>
      </StyledForm>
    </Container>
  );

  function backToList() {
    history.push('/projects');
  }
  function onCancelClick() {
    Modal.confirm({
      title: i18n.t('project.msg_sure_2_cancel'),
      icon: <ExclamationCircleOutlined />,
      content: i18n.t('project.msg_effect_of_cancel'),
      style: {
        top: '30%',
      },
      onOk: backToList,
    });
  }
  function onSubmitClick() {
    form.submit();
  }
  async function onFinish(data: any) {
    if (
      !edit &&
      certificateConfigType === CertificateConfigType.Upload &&
      data.certificates === ''
    ) {
      form.scrollToField('certificateConfigType', { block: 'center' });
      return;
    }
    setLoading(true);
    try {
      let params: CreateProjectFormData | UpdateProjectFormData;

      if (edit) {
        // Is Editting
        params = {
          variables: data.variables ?? [],
          comment: data.comment,
        };
        await onSubmit(params);
      } else {
        let participants: Participant[] = [];
        participants.push({
          name: data.participantName,
          url: data.participantUrl,
          domain_name: data.participantDomainName,
          certificates: data.certificate || null,
        });
        params = {
          name: data.name,
          config: {
            participants,
            variables: data.variables ?? [],
          },
          comment: data.comment,
        };
        await onSubmit(params);
      }
      message.success(edit ? i18n.t('project.edit_success') : i18n.t('proejct.create_success'));
      backToList();
    } catch (error) {
      message.error(error.message);
    }
    setLoading(false);
  }
}

export default BaseForm;
