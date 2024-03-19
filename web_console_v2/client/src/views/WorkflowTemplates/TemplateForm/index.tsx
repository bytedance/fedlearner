import React, { FC, useEffect, useState } from 'react';
import { Steps, Grid, Card } from '@arco-design/web-react';
import styled from './index.module.less';
import { useParams, useHistory } from 'react-router-dom';
import { useUnmount } from 'react-use';
import { useResetCreateForm } from 'hooks/template';
import StepOneBasic from './StepOneBasic';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import { definitionsStore, editorInfosStore } from './stores';
import TemplateConifg from '../TemplateConfig';

const { Step } = Steps;
const Row = Grid.Row;

enum CreateSteps {
  basic,
  jobs,
}

const TemplateForm: FC<{ isEdit?: boolean; isHydrated?: React.MutableRefObject<boolean> }> = ({
  isEdit,
  isHydrated,
}) => {
  const history = useHistory();
  const params = useParams<{ step: keyof typeof CreateSteps }>();
  const [currentStep, setStep] = useState(1);
  const [isFormValueChanged, setIsFormValueChanged] = useState(false);

  const reset = useResetCreateForm();

  useEffect(() => {
    setStep(params.step === 'basic' ? 1 : 2);
  }, [params.step]);

  useUnmount(() => {
    reset();
    definitionsStore.clearMap();
    editorInfosStore.clearMap();
  });

  return (
    <SharedPageLayout
      title={
        <BackButton
          onClick={() => history.replace(`/workflow-center/workflow-templates`)}
          isShowConfirmModal={isFormValueChanged}
        >
          模板管理
        </BackButton>
      }
      contentWrapByCard={false}
    >
      <Card>
        <Row justify="center">
          <div className={styled.step_container}>
            <Steps current={currentStep}>
              <Step title="基础信息" />
              <Step title="任务配置" />
            </Steps>
          </div>
        </Row>
      </Card>

      <div className={styled.form_area}>
        {params.step === 'basic' && (
          <StepOneBasic
            isEdit={isEdit}
            isHydrated={isHydrated}
            onFormValueChange={onFormValueChange}
          />
        )}
        {params.step === 'jobs' && <TemplateConifg isEdit={isEdit} />}
      </div>
    </SharedPageLayout>
  );

  function onFormValueChange() {
    if (!isFormValueChanged) {
      setIsFormValueChanged(true);
    }
  }
};

export default TemplateForm;
