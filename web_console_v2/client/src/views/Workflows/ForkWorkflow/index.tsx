import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Steps, Row, Card } from 'antd';
import BreadcrumbLink from 'components/BreadcrumbLink';
import { Route, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useUnmount } from 'react-use';
import { useResetForkForms } from 'hooks/workflow';
import StepOneBasic from './StepOneBasic';
import StepTwoConfig from './StepTwoConfig';

const { Step } = Steps;

const StepContainer = styled.div`
  width: 350px;
`;
const FormArea = styled.section`
  flex: 1;
  margin-top: 12px;
`;

enum ForkSteps {
  basic,
  config,
}

const ForkWorkflow: FC = () => {
  const { t } = useTranslation();
  const params = useParams<{ step: keyof typeof ForkSteps; id?: string }>();
  const [currentStep, setStep] = useState(ForkSteps[params.step || 'basic']);
  const reset = useResetForkForms();

  useUnmount(() => {
    reset();
  });

  return (
    <>
      <BreadcrumbLink
        paths={[
          { label: 'menu.label_workflow', to: '/workflows' },
          { label: 'workflow.fork_workflow' },
        ]}
      />

      <Card>
        <Row justify="center">
          <StepContainer>
            <Steps current={currentStep}>
              <Step title={t('workflow.step_basic')} />
              <Step title={t('workflow.step_config')} />
            </Steps>
          </StepContainer>
        </Row>
      </Card>

      <FormArea>
        <Route
          path={`/workflows/fork/basic/:id`}
          exact
          render={(props) => <StepOneBasic onSuccess={setToConfigStep} {...props} />}
        />
        <Route path={`/workflows/fork/config/:id`} exact component={StepTwoConfig} />
      </FormArea>
    </>
  );

  function setToConfigStep() {
    setStep(ForkSteps.config);
  }
};

export default ForkWorkflow;
