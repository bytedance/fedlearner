import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { Steps, Row, Card } from 'antd';
import BreadcrumbLink from 'components/BreadcrumbLink';
import StepOneBasic from './StepOneBasic';
import SteptTwoConfig from './SteptTwoConfig';
import { Route, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useUnmount } from 'react-use';
import { useResetCreateForms } from 'hooks/workflow';

const { Step } = Steps;

const StepContainer = styled.div`
  width: 350px;
`;
const FormArea = styled.section`
  flex: 1;
  margin-top: 12px;
  background-color: white;
`;

enum CreateSteps {
  basic,
  config,
}

const WorkflowsEdit: FC = () => {
  const { t } = useTranslation();
  const params = useParams<{ step: keyof typeof CreateSteps; id?: string }>();
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic']);
  const reset = useResetCreateForms();

  useUnmount(() => {
    reset();
  });

  return (
    <>
      <BreadcrumbLink
        paths={[
          { label: 'menu.label_workflow', to: '/workflows' },
          { label: 'workflow.edit_workflow' },
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
          path={`/workflows/edit/basic/:id`}
          exact
          render={(props) => <StepOneBasic onSuccess={setToConfigStep} {...props} />}
        />
        <Route path={`/workflows/edit/config/:id`} exact component={SteptTwoConfig} />
      </FormArea>
    </>
  );

  function setToConfigStep() {
    setStep(CreateSteps.config);
  }
};

export default WorkflowsEdit;
