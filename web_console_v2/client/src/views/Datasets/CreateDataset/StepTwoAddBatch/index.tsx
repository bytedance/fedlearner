import React, { FC, useRef, useState } from 'react';
import styled from 'styled-components';
import { message, Button, Popconfirm } from 'antd';
import { useTranslation } from 'react-i18next';
import GridRow from 'components/_base/GridRow';
import { to } from 'shared/helpers';
import { createDataset, deleteDataset } from 'services/dataset';
import AddBatchForm, { AddBatchExposedRef } from '../../AddBatchForm';
import { useRecoilValue } from 'recoil';
import { datasetBasicForm } from 'stores/dataset';

const Container = styled.div``;

type Props = {
  onCancel: any;
  onSuccess: any;
  onPrevious: any;
};

const StepTwoAddBatches: FC<Props> = ({ onSuccess, onPrevious, onCancel }) => {
  const { t } = useTranslation();
  const [datasetId, setDatasetId] = useState<ID>(null as any);
  const formRef = useRef<AddBatchExposedRef>();

  const basicForm = useRecoilValue(datasetBasicForm);

  return (
    <Container>
      <AddBatchForm
        ref={formRef as any}
        datasetId={datasetId}
        datasetType={basicForm.dataset_type}
        renderButtons={({ submitting }) => {
          return (
            <GridRow gap="12">
              <Popconfirm
                title={t('dataset.msg_quit_warning')}
                cancelText={t('cancel')}
                okText={t('submit')}
                onConfirm={onCancel}
              >
                <Button disabled={submitting}>{t('cancel')}</Button>
              </Popconfirm>

              <Button disabled={submitting} onClick={onPrevious}>
                {t('previous_step')}
              </Button>

              <Button type="primary" onClick={submitDatasetNInitiateImporting} loading={submitting}>
                {t('dataset.btn_finish_n_import')}
              </Button>
            </GridRow>
          );
        }}
      />
    </Container>
  );

  /**
   * Q: Why do we send create dataset requet at step2  not step1?
   * A: In the case of user quit the flow at step2, the dataset shouldn't be created
   */
  async function submitDatasetNInitiateImporting() {
    if (!formRef.current) return;

    const { submit: submitAddBatchForm, toggleSubmit, validate } = formRef.current;

    const isValid = await validate();

    if (!isValid) return;

    toggleSubmit(true);

    const [res, error] = await to(createDataset({ ...basicForm }));
    const datasetId = res.data.id;

    // NOTE: it's async !!!!!!
    setDatasetId(datasetId);

    if (error) {
      toggleSubmit(false);
      return message.error(error.message);
    }

    // Trigger submit add-batch form
    const [_, addBatchError] = await to(submitAddBatchForm(datasetId));

    if (addBatchError) {
      message.error(addBatchError.message);
      // TODO: what if delete request also failed?
      try {
        deleteDataset(datasetId);
      } catch {
        /** ignore error */
      }
      toggleSubmit(false);
      return;
    }

    message.success(t('dataset.msg_start_importing'));
    toggleSubmit(false);
    // Tell parent the happy news
    onSuccess();
  }
};

export default StepTwoAddBatches;
