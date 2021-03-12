import React, { FC, useState } from 'react';
import { Form, Input, Button, Tooltip, notification, message } from 'antd';
import ListPageLayout from 'components/ListPageLayout';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { useMutation, useQuery } from 'react-query';
import { fetchSettings, updateSettings } from 'services/settings';
import { QuestionCircle, Close } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import { SettingOptions } from 'typings/settings';

const StyledForm = styled(Form)`
  width: 500px;
  margin: 30vh auto auto;
`;
const SubmitButton = styled(Button)`
  width: 100%;
`;

const SettingsPage: FC = () => {
  const { t } = useTranslation();
  const [formInstance] = Form.useForm<SettingOptions>();
  const [currentImage, setImage] = useState<string>();

  const query = useQuery('fetchSettings', fetchSettings, {
    onSuccess(res) {
      setImage(res.data.webconsole_image);
      formInstance.setFieldsValue({ ...res.data });
    },
    refetchOnWindowFocus: false,
    retry: 2,
  });

  const mutation = useMutation(updateSettings, {
    onSuccess() {
      const isImageChanged = formInstance.getFieldValue('webconsole_image') !== currentImage;

      if (isImageChanged) {
        notification.info({
          message: t('settings.msg_update_success'),
          description: t('settings.msg_update_wc_image'),
          duration: 2 * 60, // 2min
          closeIcon: <Close />,
        });
      } else {
        message.success(t('settings.msg_update_success'));
      }
    },
  });

  return (
    <ListPageLayout title={t('menu.label_settings')}>
      <StyledForm
        form={formInstance}
        onFinish={onFinish}
        labelCol={{ span: 6 }}
        wrapperCol={{ span: 18 }}
      >
        <Form.Item
          name="webconsole_image"
          label={
            <GridRow gap="4">
              {t('settings.label_image_ver')}
              <Tooltip title={t('settings.hint_update_image')}>
                <QuestionCircle />
              </Tooltip>
            </GridRow>
          }
          rules={[{ required: true, message: t('settings.msg_image_required') }]}
        >
          <Input
            placeholder={t('settings.placeholder_image')}
            disabled={query.isFetching || mutation.isLoading}
          />
        </Form.Item>

        <Form.Item wrapperCol={{ offset: 6 }}>
          <SubmitButton
            disabled={query.isFetching}
            type="primary"
            htmlType="submit"
            loading={mutation.isLoading}
          >
            {t('submit')}
          </SubmitButton>
        </Form.Item>
      </StyledForm>
    </ListPageLayout>
  );

  async function onFinish(values: any) {
    mutation.mutate(values);
  }
};

export default SettingsPage;
