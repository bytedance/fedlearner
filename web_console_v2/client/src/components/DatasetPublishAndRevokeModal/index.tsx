import React, { FC, useMemo } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';

import { postPublishDataset, unpublishDataset } from 'services/dataset';

import { Modal, Form, Message, InputNumber, Space } from '@arco-design/web-react';
import datasetPublishBg from 'assets/images/dataset-publish-bg.png';
import { Dataset } from 'typings/dataset';
import creditsIcon from 'assets/icons/credits-icon.svg';
import i18n from 'i18n';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { CREDITS_LIMITS } from 'views/Datasets/shared';
import { useGetAppFlagValue } from 'hooks';
import { FlagKey } from 'typings/flag';

const ContainerModal = styled(Modal)<{ $isPublish: boolean }>`
  ${(prop) =>
    prop.$isPublish
      ? `
      .arco-modal-content{
        padding: 0;
      }
      `
      : ''}
  .arco-modal-header {
    border-bottom: 0;
  }
  .arco-modal-footer {
    border-top: 0;
    text-align: center;
  }
`;

const StyledPublishContent = styled.div`
  height: 88px;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  align-items: center;
  background-image: url(${datasetPublishBg});
  background-size: cover;
`;

const StyledForm = styled(Form)`
  width: 140px;
  margin: 16px auto 0;
` as typeof Form;

const StyledInputNumber = styled(InputNumber)`
  width: 140px;
`;

const StyledCreditIcon = styled.img`
  display: inline-block;
`;

const StyledSpace = styled(Space)`
  width: 100%;
  height: 32px;
  background: #e8f4ff;
  justify-content: center;
`;

const StyleTitleSpace = styled(Space)`
  width: 100%;
  justify-content: center;
`;

enum OPERATION_TYPE {
  PUBLISH = 'publish',
  REVOKE = 'revoke',
}

export interface Props {
  visible: boolean;
  dataset?: Dataset;
  onSuccess?: () => void;
  onFail?: () => void;
  onCancel?: () => void;
}

interface FormData {
  value: number;
}

const DatasetPublishAndRevokeModal: FC<Props> = ({
  dataset,
  visible,
  onSuccess,
  onFail,
  onCancel,
}) => {
  const bcs_support_enabled = useGetAppFlagValue(FlagKey.BCS_SUPPORT_ENABLED);
  const { t } = useTranslation();
  const formData: FormData = {
    value: !dataset?.value ? 100 : dataset?.value,
  };
  const [formInstance] = Form.useForm<FormData>();
  const willUnpublished = useMemo(() => {
    if (!dataset?.is_published) {
      return false;
    }
    return dataset.is_published === true;
  }, [dataset]);

  return (
    <ContainerModal
      $isPublish={!willUnpublished}
      closable={false}
      visible={visible}
      onConfirm={handleOnConfirm}
      onCancel={handleOnCancel}
      maskClosable={false}
      okText={t(willUnpublished ? OPERATION_TYPE.REVOKE : OPERATION_TYPE.PUBLISH)}
      cancelText={t('cancel')}
      okButtonProps={{
        status: willUnpublished ? 'danger' : 'default',
      }}
      title={willUnpublished ? renderTitle() : null}
    >
      {willUnpublished ? renderRevoke() : renderPublish()}
    </ContainerModal>
  );

  async function handleOnConfirm() {
    if (!dataset) {
      return;
    }
    try {
      if (willUnpublished) {
        await unpublishDataset(dataset.id);
      } else {
        const value = formInstance.getFieldValue('value');
        await postPublishDataset(dataset.id, {
          value,
        });
      }
      Message.success(t(willUnpublished ? 'message_revoke_success' : 'message_publish_success'));
      formInstance.resetFields('value');
      onSuccess?.();
    } catch (e) {
      Message.error(t(willUnpublished ? 'message_revoke_failed' : 'message_publish_failed'));
      formInstance.resetFields('value');
      onFail?.();
    }
  }

  function handleOnCancel() {
    formInstance.resetFields('value');
    onCancel?.();
  }

  function renderPublish() {
    return (
      <>
        <StyledPublishContent>
          <span>
            {t(`dataset.msg_publish_confirm`, {
              name: dataset?.name,
            })}
          </span>
          <span>{t('dataset.tips_publish')}</span>
        </StyledPublishContent>
        {/*temporary solution for no metadata*/}
        {!!bcs_support_enabled && renderFirstPublishTips(dataset?.value || 0)}
        {!!bcs_support_enabled && (
          <StyledForm initialValues={formData} layout="vertical" form={formInstance}>
            <Form.Item field="value" label={t('dataset.label_use_price')}>
              <StyledInputNumber
                min={CREDITS_LIMITS.MIN}
                max={CREDITS_LIMITS.MAX}
                suffix={t('dataset.label_publish_credits')}
                step={1}
              />
            </Form.Item>
          </StyledForm>
        )}
      </>
    );
  }

  function renderRevoke() {
    return <StyleTitleSpace>{t(`dataset.msg_unpublish_tip`)}</StyleTitleSpace>;
  }

  function renderTitle() {
    return (
      <StyleTitleSpace>
        <IconInfoCircle style={{ color: '#FA9600' }} />
        {t(`dataset.msg_unpublish_confirm`, {
          name: dataset?.name,
        })}
      </StyleTitleSpace>
    );
  }

  function renderFirstPublishTips(price: number = 0) {
    if (price > 0) {
      return null;
    }
    return (
      <StyledSpace align="center">
        <StyledCreditIcon src={creditsIcon} />
        {i18n.t('dataset.tips_first_publish')}
      </StyledSpace>
    );
  }
};

export default DatasetPublishAndRevokeModal;
