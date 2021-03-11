import React, { FC, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Steps, Row, Card } from 'antd';
import styled from 'styled-components';
import BreadcrumbLink from 'components/BreadcrumbLink';
import { Route, useParams } from 'react-router-dom';
import { useUnmount } from 'react-use';
import { useResetCreateForm } from 'hooks/template';
import StepOneBasic from './StepOneBasic';
import StepTwoJobs from './StepTwoJobs';

const { Step } = Steps;

const StepContainer = styled.div`
  width: 350px;
`;
const FormArea = styled.section`
  flex: 1;
  margin-top: 12px;
`;

enum CreateSteps {
  basic,
  jobs,
}

const CreateTemplate: FC = () => {
  const { t } = useTranslation();
  const params = useParams<{ step: keyof typeof CreateSteps; id?: string }>();
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic']);
  const reset = useResetCreateForm();

  useEffect(() => {
    setStep(CreateSteps[params.step || 'basic']);
  }, [params.step]);

  useUnmount(() => {
    reset();
  });

  return (
    <>
      <BreadcrumbLink
        paths={[
          { label: 'menu.label_workflow_tpl', to: '/workflow-templates' },
          { label: 'workflow.create_tpl' },
        ]}
      />

      <Card>
        <Row justify="center">
          <StepContainer>
            <Steps current={currentStep}>
              <Step title={t('workflow.step_tpl_basic')} />
              <Step title={t('workflow.step_tpl_config')} />
            </Steps>
          </StepContainer>
        </Row>
      </Card>

      <FormArea>
        <Route path={`/workflow-templates/create/basic`} exact component={StepOneBasic} />
        <Route path={`/workflow-templates/create/jobs`} exact component={StepTwoJobs} />
      </FormArea>
    </>
  );
};

export default TemplateCreate;
