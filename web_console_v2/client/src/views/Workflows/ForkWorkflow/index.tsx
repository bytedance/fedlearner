import React, { FC, useState } from 'react';
import styled from './index.module.less';
import { Steps, Grid, Card } from '@arco-design/web-react';
import { Route, useParams, useHistory } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useUnmount } from 'react-use';
import { useResetForkForms } from 'hooks/workflow';
import StepOneBasic from './StepOneBasic';
import StepTwoConfig from './StepTwoConfig';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';

const { Step } = Steps;
const Row = Grid.Row;

enum ForkSteps {
  basic,
  config,
}

const ForkWorkflow: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{ step: keyof typeof ForkSteps; id?: string }>();
  const [currentStep, setStep] = useState(ForkSteps[params.step || 'basic'] + 1);
  const [isFormValueChanged, setIsFormValueChanged] = useState(false);

  const reset = useResetForkForms();

  useUnmount(() => {
    // Reset forms after leave
    reset();
  });

  return (
    <SharedPageLayout
      title={
        <BackButton
          onClick={() => history.replace(`/workflow-center/workflows`)}
          isShowConfirmModal={isFormValueChanged}
        >
          {t('menu.label_workflow')}
        </BackButton>
      }
      contentWrapByCard={false}
    >
      <Card>
        <Row justify="center">
          <div className={styled.step_container}>
            <Steps current={currentStep}>
              <Step title={t('workflow.step_basic')} />
              <Step title={t('workflow.step_config')} />
            </Steps>
          </div>
        </Row>
      </Card>

      <section className={styled.form_area}>
        <Route
          path={`/workflow-center/workflows/fork/basic/:id`}
          exact
          render={(props) => (
            <StepOneBasic
              onSuccess={setToConfigStep}
              onFormValueChange={onFormValueChange}
              {...props}
            />
          )}
        />
        <Route
          path={`/workflow-center/workflows/fork/config/:id`}
          exact
          component={StepTwoConfig}
        />
      </section>
    </SharedPageLayout>
  );

  function setToConfigStep() {
    setStep(ForkSteps['config'] + 1);
  }
  function onFormValueChange() {
    if (!isFormValueChanged) {
      setIsFormValueChanged(true);
    }
  }
};

export default ForkWorkflow;
