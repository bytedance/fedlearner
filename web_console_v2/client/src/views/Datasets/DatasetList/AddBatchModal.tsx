import React, { FC, useRef } from 'react';
import { Modal, Button, message } from 'antd';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import IconButton from 'components/IconButton';
import { useTranslation } from 'react-i18next';
import { Close } from 'components/IconPark';
import { DatasetType } from 'typings/dataset';
import AddBatchForm, { AddBatchExposedRef } from '../AddBatchForm';
import { to } from 'shared/helpers';
import GridRow from 'components/_base/GridRow';
import styled from 'styled-components';

const ContainerModal = styled(Modal)`
  .ant-modal-body {
    padding-bottom: 14px;
  }
  .ant-modal-footer {
    display: none;
  }
`;

type Props = {
  datasetId?: ID;
  datasetType?: DatasetType;
  visible: boolean;
  toggleVisible: (v: boolean) => void;
  onSuccess: Function;
} & React.ComponentProps<typeof Modal>;

const AddBatchBatch: FC<Props> = ({
  datasetId,
  datasetType,
  visible,
  toggleVisible,
  onSuccess,
  ...props
}) => {
  const { t } = useTranslation();
  const formRef = useRef<AddBatchExposedRef>();

  return (
    <ContainerModal
      title={t('dataset.title_create')}
      visible={visible}
      width={900}
      style={{ top: '10%' }}
      closeIcon={<IconButton icon={<Close />} onClick={closeModal} />}
      zIndex={Z_INDEX_GREATER_THAN_HEADER}
      onCancel={closeModal}
      okText={t('confirm')}
      {...props}
    >
      <AddBatchForm
        ref={formRef as any}
        datasetId={datasetId}
        datasetType={datasetType}
        renderButtons={({ submitting }) => {
          return (
            <GridRow gap="12">
              <Button disabled={submitting} onClick={closeModal}>
                {t('cancel')}
              </Button>

              <Button type="primary" onClick={submit} loading={submitting}>
                {t('dataset.btn_import')}
              </Button>
            </GridRow>
          );
        }}
      />
    </ContainerModal>
  );

  function closeModal() {
    toggleVisible(false);
  }
  async function submit() {
    if (!formRef.current) return;

    if (!datasetType || !datasetId) {
      return message.error('缺少 ID 或 Type');
    }

    const { submit: submitAddBatchForm, toggleSubmit, validate } = formRef.current;

    const isValid = await validate();

    if (!isValid) return;

    const [res, error] = await to(submitAddBatchForm());

    if (error) {
      message.error(error.message);
      toggleSubmit(false);
      return;
    }

    message.success(t('dataset.msg_start_importing'));
    toggleSubmit(false);
    closeModal();

    onSuccess(res);
  }
};

export default AddBatchBatch;
