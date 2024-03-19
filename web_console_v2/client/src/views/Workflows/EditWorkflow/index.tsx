import React, { FC, useState, useEffect } from 'react';
import styled from './index.module.less';
import { Steps, Grid, Card } from '@arco-design/web-react';
import StepOneBasic from './StepOneBasic';
import SteptTwoConfig from './SteptTwoConfig';
import { Route, useHistory, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useUnmount } from 'react-use';
import { useResetCreateForms } from 'hooks/workflow';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';

const { Step } = Steps;
const Row = Grid.Row;

enum CreateSteps {
  basic,
  config,
}

const WorkflowsEdit: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const params = useParams<{ step: keyof typeof CreateSteps; id?: string }>();
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic'] + 1);
  const [isFormValueChanged, setIsFormValueChanged] = useState(false);
  const reset = useResetCreateForms();

  useEffect(() => {
    setStep(CreateSteps[params.step || 'basic'] + 1);
  }, [params.step]);

  useUnmount(() => {
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
          path={`/workflow-center/workflows/edit/basic/:id`}
          exact
          render={() => <StepOneBasic onFormValueChange={onFormValueChange} />}
        />
        <Route
          path={`/workflow-center/workflows/edit/config/:id`}
          exact
          component={SteptTwoConfig}
        />
      </section>
    </SharedPageLayout>
  );

  function onFormValueChange() {
    if (!isFormValueChanged) {
      setIsFormValueChanged(true);
    }
  }
};

export default WorkflowsEdit;
