import React, { FC, useState, useRef } from 'react';
import styled from './index.module.less';
import { useQuery } from 'react-query';

import { fetchSettingVariables, updateSettingVariables } from 'services/settings';
import { formatValueToString, parseValueFromString } from 'shared/helpers';

import { Form, Button, Message, Spin } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout from 'components/SharedPageLayout';
import Modal from 'components/Modal';
import EnvVariablesForm, {
  VARIABLES_FIELD_NAME,
  VARIABLES_ERROR_CHANNEL,
} from './EnvVariablesForm';

import { FormProps } from '@arco-design/web-react/es/Form';
import { SettingOptions, SystemVariable } from 'typings/settings';

const layout = {
  labelCol: { span: 8 },
  wrapperCol: { span: 16 },
};
const Systemvariables: FC = () => {
  const [form] = Form.useForm();

  const [loading, setLoading] = useState(false);
  const defaultVariables = useRef<SystemVariable[]>([]);

  const systemVariablesQuery = useQuery(['fetchSettingVariables'], () => fetchSettingVariables(), {
    onSuccess(res) {
      const variables: SystemVariable[] = (res.data?.variables ?? []).map((item) => {
        return {
          ...item,
          value: formatValueToString(item.value, item.value_type),
        };
      });

      defaultVariables.current = variables;
      form.setFieldsValue({
        variables: variables,
      });
    },
    onError(error: any) {
      Message.error(error.message);
    },
    cacheTime: 1,
    refetchOnWindowFocus: false,
  });

  return (
    <SharedPageLayout title={'全局配置'}>
      <Form
        className={styled.styled_form}
        form={form}
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 18 }}
        onSubmit={onFinish}
        onSubmitFailed={onFinishFailed}
      >
        <Spin loading={systemVariablesQuery.isFetching}>
          <EnvVariablesForm layout={layout} formInstance={form} disabled={loading} />
        </Spin>
        <Form.Item
          wrapperCol={{ offset: 3 }}
          style={{
            width: 'calc(var(--form-width, 500px) * 2)',
          }}
        >
          <GridRow gap="16">
            <Button type="primary" loading={loading} onClick={onSubmitClick}>
              {'确认'}
            </Button>
            <Button onClick={onCancelClick}>{'取消'}</Button>
          </GridRow>
        </Form.Item>
      </Form>
    </SharedPageLayout>
  );

  function resetForm() {
    form.setFieldsValue({
      variables: defaultVariables.current,
    });
  }
  function onCancelClick() {
    Modal.confirm({
      title: '确认取消？',
      content: '取消后，已填写内容将不再保留',
      onOk: resetForm,
    });
  }
  function onSubmitClick() {
    form.submit();
  }
  async function onFinish(data: any) {
    setLoading(true);
    try {
      const params: SettingOptions = {
        webconsole_image: undefined,
        variables: (data.variables ?? []).map((item: SystemVariable) => {
          return {
            ...item,
            value: parseValueFromString(item.value, item.value_type),
          };
        }),
      };

      const systemVariables = await updateSettingVariables({ variables: params.variables });
      Message.success('修改环境变量成功');
      defaultVariables.current = systemVariables.data?.variables ?? [];
    } catch (error) {
      Message.error(error.message);
    }
    setLoading(false);
  }
  function onFinishFailed(errorInfo: Parameters<Required<FormProps>['onSubmitFailed']>[0]) {
    const regx = new RegExp(`^${VARIABLES_FIELD_NAME}`);
    if (Object.keys(errorInfo).some((key) => regx.test(key))) {
      PubSub.publish(VARIABLES_ERROR_CHANNEL);
    }
  }
};

export default Systemvariables;
