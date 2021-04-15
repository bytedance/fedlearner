import { Button, Card, Form, Input, Radio } from 'antd';
import BreadcrumbLink from 'components/BreadcrumbLink';
import GridRow from 'components/_base/GridRow';
import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { useHistory } from 'react-router-dom';
import { useToggle } from 'react-use';
import styled from 'styled-components';
import { FedUserInfo } from 'typings/auth';

const StyledCard = styled(Card)`
  flex: 1;
`;
const StyledForm = styled(Form)`
  width: 600px;
  margin: 0 auto;
  background-color: white;
  padding-top: 80px;
`;

const UserForm: FC<{ isEdit?: boolean; onSubmit?: any; initialValues?: any }> = ({
  isEdit,
  onSubmit,
  initialValues,
}) => {
  const { t } = useTranslation();
  const [form] = Form.useForm<FedUserInfo>();
  const history = useHistory();
  const [submitting, toggleSubmitting] = useToggle(false);

  return (
    <>
      <BreadcrumbLink
        paths={[
          { label: 'menu.label_users', to: '/users' },
          { label: isEdit ? 'users.title_user_edit' : 'users.title_user_create' },
        ]}
      />
      <StyledCard bordered={false}>
        <StyledForm
          labelCol={{ span: 6 }}
          wrapperCol={{ span: 14 }}
          initialValues={initialValues}
          form={form}
          onFinish={onFinish}
        >
          <Form.Item name="id" label={t('users.col_id')} hidden={!isEdit}>
            <Input disabled={true} />
          </Form.Item>
          <Form.Item name="username" label={t('users.col_username')} rules={[{ required: true }]}>
            <Input disabled={isEdit} placeholder={t('users.placeholder_username')} />
          </Form.Item>
          <Form.Item
            name="password"
            label={t('users.col_password')}
            rules={[{ required: !isEdit }]}
          >
            <Input placeholder={t('users.placeholder_password')} />
          </Form.Item>
          <Form.Item name="name" label={t('users.col_name')} rules={[{ required: true }]}>
            <Input placeholder={t('users.placeholder_name')} />
          </Form.Item>
          <Form.Item name="email" label={t('users.col_email')} rules={[{ required: true }]}>
            <Input placeholder={t('users.placeholder_email')} />
          </Form.Item>
          <Form.Item name="role" label={t('users.col_role')} rules={[{ required: true }]}>
            <Radio.Group>
              <Radio.Button value="USER">{t('users.role_user')}</Radio.Button>
              <Radio.Button value="ADMIN">{t('users.role_admin')}</Radio.Button>
            </Radio.Group>
          </Form.Item>

          <Form.Item wrapperCol={{ offset: 6 }}>
            <GridRow gap={16} top="12">
              <Button loading={submitting} type="primary" htmlType="submit">
                {t('users.btn_submit')}
              </Button>

              <Button disabled={submitting} onClick={backToList}>
                {t('cancel')}
              </Button>
            </GridRow>
          </Form.Item>
        </StyledForm>
      </StyledCard>
    </>
  );
  async function backToList() {
    history.push('/users');
  }

  async function onFinish(data: any) {
    try {
      toggleSubmitting(true);
      await onSubmit(data);
    } catch {
      // ignore error
    } finally {
      toggleSubmitting(false);
    }
  }
};

export default UserForm;
