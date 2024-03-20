import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Form, Input, Button, message, Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import SecondaryForm from './SecondaryForm';
import EnvVariablesForm, {
  VARIABLES_FIELD_NAME,
  VARIABLES_ERROR_CHANNEL,
} from './EnvVariablesForm';
import { CertificateConfigType } from 'typings/project';
import {
  ProjectFormInitialValues,
  CreateProjectPayload,
  UpdateProjectPayload,
  Participant,
} from 'typings/project';
import { useHistory } from 'react-router-dom';
import GridRow from 'components/_base/GridRow';
import i18n from 'i18n';
import { useReloadProjectList } from 'hooks/project';
import ip from 'ip-port-regex';
import Certificate from './Certificate';
import { DOMAIN_PREFIX, DOMAIN_SUFFIX, wrapWithDomainName } from 'shared/project';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import { FormHeader } from 'components/SharedPageLayout';

const Container = styled.div`
  flex: 1;
`;
const StyledForm = styled(Form)`
  --form-width: 500px;

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

const layout = {
  labelCol: { span: 8 },
  wrapperCol: { span: 16 },
};

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

interface Props {
  onSubmit: (payload: any) => Promise<void>;
  isEdit?: boolean;
  initialValues?: ProjectFormInitialValues;
}

const ProjectForm: FC<Props> = ({ onSubmit, isEdit, initialValues }) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [isCertRequired, setCertRequired] = useState(!isEdit);
  const history = useHistory();
  const defaultValues: ProjectFormInitialValues = initialValues ?? defaultInitialValues;

  const reloadList = useReloadProjectList();
  const domainRules = [
    { required: true, message: t('project.msg_domian_required') },
    { pattern: /^[0-9a-z-]+$/g, message: t('project.msg_domian_invalid') },
  ];

  return (
    <Container>
      <FormHeader>{isEdit ? '编辑项目' : '创建项目'}</FormHeader>
      <StyledForm
        {...layout}
        initialValues={defaultValues}
        form={form}
        colon={false}
        onFinish={onFinish}
        onFinishFailed={onFinishFailed}
        scrollToFirstError
      >
        {/* Project Config */}
        <SecondaryForm title={t('project.basic_information')}>
          <Form.Item
            hasFeedback
            name="name"
            label={t('project.name')}
            rules={[{ required: true, message: t('project.name_message') }]}
          >
            <Input
              name="name"
              placeholder={t('project.name_placeholder')}
              disabled={isEdit || loading}
            />
          </Form.Item>
          {/* FIXME:  Enable Token input after API support */}
          {/* <Form.Item
            name="token"
            label={t('project.label_token')}
            rules={[
              { required: true, message: t('project.msg_token_required') },
              { pattern: /^[a-zA-Z0-9]{0,64}$/g, message: t('project.msg_token_invalid') },
            ]}
          >
            <Input placeholder={t('project.placeholder_token')} disabled={isEdit || loading} />
          </Form.Item> */}
        </SecondaryForm>

        {/* Participant config */}
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
              disabled={loading}
            />
          </Form.Item>

          <Form.Item
            name="participantDomainName"
            label={t('project.participant_domain')}
            rules={domainRules}
          >
            <Input
              name="participantDomainName"
              addonBefore={DOMAIN_PREFIX}
              addonAfter={DOMAIN_SUFFIX}
              placeholder={t('project.placeholder_domain_name')}
              disabled={isEdit || loading}
            />
          </Form.Item>

          <Form.Item
            hidden={isEdit && !isCertRequired && !Boolean(initialValues?.participantUrl)}
            hasFeedback
            name="participantUrl"
            label={t('project.participant_url')}
            rules={[
              { required: isCertRequired, message: t('project.participant_url_message') },
              {
                validator(_, value) {
                  if (!isCertRequired) return Promise.resolve();

                  if (ip({ exact: true }).test(value)) {
                    return Promise.resolve();
                  } else {
                    return Promise.reject(t('project.msg_ip_addr_invalid'));
                  }
                },
              },
            ]}
          >
            <Input
              name="participantUrl"
              placeholder={t('project.placeholder_participant_url')}
              disabled={isEdit || loading}
            />
          </Form.Item>

          <Form.Item
            name="certificate"
            label={t('certificate')}
            rules={[{ required: isCertRequired, message: t('project.upload_certificate_message') }]}
          >
            <Certificate
              isEdit={isEdit}
              onTypeChange={(val) => {
                setCertRequired(val === CertificateConfigType.Upload);
              }}
              disabled={loading}
            />
          </Form.Item>

          <Form.Item name="comment" label={t('project.remarks')}>
            <Input.TextArea
              rows={4}
              style={{ resize: 'none' }}
              name="comment"
              disabled={loading}
              placeholder={t('project.remarks_placeholder')}
            />
          </Form.Item>

          <EnvVariablesForm layout={layout} formInstance={form} disabled={loading} />
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
      zIndex: Z_INDEX_GREATER_THAN_HEADER,
      getContainer: 'body',
      style: {
        top: '30%',
      },
      onOk: backToList,
    });
  }
  function onSubmitClick() {
    form.submit();
  }
  function onFinishFailed({ errorFields }: any) {
    if (
      errorFields.some(
        (item: any) =>
          item.name === VARIABLES_FIELD_NAME || item.name.includes(VARIABLES_FIELD_NAME),
      )
    ) {
      PubSub.publish(VARIABLES_ERROR_CHANNEL);
    }
  }
  async function onFinish(data: any) {
    if (!isEdit && data.certificates === '') {
      form.scrollToField('certificateConfigType', { block: 'center' });
      return;
    }

    setLoading(true);

    try {
      let params: CreateProjectPayload | UpdateProjectPayload;

      if (isEdit) {
        params = {
          participant_name: data.participantName,
          variables: data.variables ?? [],
          comment: data.comment,
        };
        await onSubmit(params);
      } else {
        let participants: Participant[] = [];
        participants.push({
          name: data.participantName,
          url: data.participantUrl,
          domain_name: wrapWithDomainName(data.participantDomainName),
          certificates: data.certificate || null,
        });

        params = {
          name: data.name,
          config: {
            token: data.token || '',
            participants,
            variables: data.variables ?? [],
          },
          comment: data.comment,
        };
        await onSubmit(params);
      }
      message.success(isEdit ? i18n.t('project.edit_success') : i18n.t('project.create_success'));
      reloadList();
      backToList();
    } catch (error) {
      message.error(error.message);
    }
    setLoading(false);
  }
};

export default ProjectForm;
