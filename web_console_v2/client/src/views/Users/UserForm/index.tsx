import React, { FC } from 'react';
import { useHistory } from 'react-router-dom';
import { useToggle } from 'react-use';
import styled from './index.module.less';

import { validNamePattern, validEmailPattern, validPasswordPattern } from 'shared/validator';

import { Button, Form, Input, Radio } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout, { FormHeader } from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';

import { FedUserInfo } from 'typings/auth';

const UserForm: FC<{ isEdit?: boolean; onSubmit?: any; initialValues?: any }> = ({
  isEdit,
  onSubmit,
  initialValues,
}) => {
  const [form] = Form.useForm<FedUserInfo>();
  const history = useHistory();
  const [submitting, toggleSubmitting] = useToggle(false);

  return (
    <SharedPageLayout
      title={<BackButton onClick={() => history.goBack()}>{'用户管理'}</BackButton>}
    >
      <FormHeader>{isEdit ? '编辑用户' : '创建用户'}</FormHeader>
      <Form
        className={styled.styled_form}
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 14 }}
        initialValues={initialValues}
        form={form}
        onSubmit={onFinish}
      >
        <Form.Item field="id" label={'ID'} hidden={!isEdit}>
          <Input disabled={true} />
        </Form.Item>
        <Form.Item
          field="username"
          label={'用户名'}
          rules={[
            { required: true },
            {
              match: validNamePattern,
              message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
            },
          ]}
        >
          <Input disabled={isEdit} placeholder={'请输入用户名'} />
        </Form.Item>
        <Form.Item
          field="password"
          label={'密码'}
          rules={[
            { required: !isEdit },
            {
              match: validPasswordPattern,
              message:
                '请输入正确的密码格式，至少包含一个字母、一个数字、一个特殊字符，且长度在8到20之间',
            },
          ]}
        >
          <Input placeholder={'请输入登陆密码'} />
        </Form.Item>
        <Form.Item
          field="name"
          label={'名称'}
          rules={[
            { required: true },
            {
              match: validNamePattern,
              message: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
            },
          ]}
        >
          <Input placeholder={'请输入用户昵称'} />
        </Form.Item>
        <Form.Item
          field="email"
          label={'邮箱'}
          rules={[
            { required: true },
            { match: validEmailPattern, message: '请输入正确的邮箱格式' },
          ]}
        >
          <Input placeholder={'请输入用户邮箱'} />
        </Form.Item>
        <Form.Item field="role" label={'角色'} rules={[{ required: true }]}>
          <Radio.Group type="button">
            <Radio value="USER">{'普通用户'}</Radio>
            <Radio value="ADMIN">{'管理员'}</Radio>
          </Radio.Group>
        </Form.Item>

        <Form.Item wrapperCol={{ offset: 6 }}>
          <GridRow gap={16} top="12">
            <Button loading={submitting} type="primary" htmlType="submit">
              {'提交'}
            </Button>

            <Button disabled={submitting} onClick={backToList}>
              {'取消'}
            </Button>
          </GridRow>
        </Form.Item>
      </Form>
    </SharedPageLayout>
  );
  async function backToList() {
    history.push('/users');
  }

  async function onFinish(data: any) {
    try {
      toggleSubmitting(true);
      if (data.password) {
        data.password = btoa(data.password);
      }
      await onSubmit(data);
    } catch {
      // ignore error
    } finally {
      toggleSubmitting(false);
    }
  }
};

export default UserForm;
