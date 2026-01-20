import React, { FC, useState } from 'react';
import styled from './index.module.less';
import { useMutation, useQuery } from 'react-query';

import { fetchSettingsImage, updateImage } from 'services/settings';

import { Form, Input, Button, Tooltip, Notification, Message } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import { QuestionCircle } from 'components/IconPark';

import { SettingOptions } from 'typings/settings';

const ImageVersion: FC = () => {
  const [formInstance] = Form.useForm<SettingOptions>();
  const [currentImage, setImage] = useState<string>();

  const query = useQuery('fetchSettingsImage', fetchSettingsImage, {
    onSuccess(res) {
      setImage(res.data.value);
      formInstance.setFieldsValue({ webconsole_image: res.data.value });
    },
    onError(error: any) {
      Message.error(error.message);
    },
    refetchOnWindowFocus: false,
    retry: 2,
  });

  const mutation = useMutation(updateImage, {
    onSuccess() {
      const isImageChanged = formInstance.getFieldValue('webconsole_image') !== currentImage;

      if (isImageChanged) {
        Notification.info({
          title: '系统配置更新成功',
          content:
            '已启动更新程序，Pod 开始进行替换，完成后可能需要手动 Port forward，并且该窗口将在几分钟后变得不可用。',
          duration: 2 * 1000 * 60, // 2min
        });
      } else {
        Message.success('编辑成功');
      }
    },
  });

  return (
    <SharedPageLayout title={'全局配置'}>
      <Form
        className={styled.styled_form}
        form={formInstance}
        onSubmit={onFinish}
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 18 }}
      >
        <Form.Item
          field="webconsole_image"
          label={
            <>
              <span style={{ marginRight: 4 }}>{'镜像版本'}</span>
              <Tooltip content={'每次更新 Web Console 镜像版本后需等待一段时间，刷新页面后才可用'}>
                <QuestionCircle />
              </Tooltip>
            </>
          }
          rules={[{ required: true, message: '镜像版本为必填项' }]}
        >
          <Input placeholder={'请选择镜像版本'} disabled={query.isFetching || mutation.isLoading} />
        </Form.Item>

        <Form.Item wrapperCol={{ offset: 6, span: 18 }}>
          <Button
            disabled={query.isFetching}
            type="primary"
            htmlType="submit"
            loading={mutation.isLoading}
            long
          >
            {'确认'}
          </Button>
        </Form.Item>
      </Form>
    </SharedPageLayout>
  );

  async function onFinish(values: any) {
    mutation.mutate(values);
  }
};

export default ImageVersion;
