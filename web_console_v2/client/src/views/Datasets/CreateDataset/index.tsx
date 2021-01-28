import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Modal } from 'antd';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import { useHistory } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useToggle } from 'react-use';
import { Steps, Row } from 'antd';
import StepOneBasic from './StepOneBasic';
import StepTwoAddBatch from './StepTwoAddBatch';
import { useResetCreateForm } from 'hooks/dataset';

const ContainerModal = styled(Modal)`
  .ant-modal-body {
    padding-bottom: 14px;
  }
  .ant-modal-footer {
    display: none;
  }
`;
const StepRow = styled(Row)`
  width: 340px;
  margin: 10px auto 35px;
`;

const zIndex = Z_INDEX_GREATER_THAN_HEADER;

const CreateDataset: FC = () => {
  const history = useHistory();
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const [visible, toggleVisible] = useToggle(true);

  const resetForm = useResetCreateForm();

  return (
    <ContainerModal
      title={t('dataset.title_create')}
      visible={visible}
      style={{ top: '20%' }}
      width="fit-content"
      closable={false}
      maskClosable={false}
      keyboard={false}
      afterClose={afterClose}
      getContainer="body"
      zIndex={zIndex}
      onCancel={() => toggleVisible(false)}
    >
      <StepRow justify="center">
        <Steps current={step} size="small">
          <Steps.Step title={t('dataset.step_basic')} />
          <Steps.Step title={t('dataset.step_add_batch')} />
        </Steps>
      </StepRow>

      {step === 0 && <StepOneBasic onSuccess={goAddBatch} onCancel={closeModal} />}

      {step === 1 && (
        <StepTwoAddBatch
          onSuccess={onCreateNStartImportSuccess}
          onPrevious={backToStepBasic}
          onCancel={closeModal}
        />
      )}
    </ContainerModal>
  );

  function afterClose() {
    history.push('/datasets');
  }
  function goAddBatch() {
    setStep(1);
  }
  function backToStepBasic() {
    setStep(0);
  }
  function closeModal() {
    resetForm();
    toggleVisible(false);
  }
  function onCreateNStartImportSuccess() {
    closeModal();
  }
};

export default CreateDataset;
