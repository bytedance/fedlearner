import React, { FC, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Steps, Row, Card } from 'antd';
import styled from 'styled-components';
import BreadcrumbLink from 'components/BreadcrumbLink';
import { useParams } from 'react-router-dom';
import { useUnmount } from 'react-use';
import { useResetCreateForm } from 'hooks/template';
import StepOneBasic from './StepOneBasic';
import StepTwoJobs from './StepTwoJobs';
import { clearMap } from './store';

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

const TemplateForm: FC<{ isEdit?: boolean; isHydrated?: React.MutableRefObject<boolean> }> = ({
  isEdit,
  isHydrated,
}) => {
  const { t } = useTranslation();
  const params = useParams<{ step: keyof typeof CreateSteps }>();
  const [currentStep, setStep] = useState(CreateSteps[params.step || 'basic']);
  const reset = useResetCreateForm();

  useEffect(() => {
    setStep(CreateSteps[params.step || 'basic']);
  }, [params.step]);

  useUnmount(() => {
    reset();
    clearMap();
  });

  return (
    <>
      <BreadcrumbLink
        paths={[
          { label: 'menu.label_workflow_tpl', to: '/workflow-templates' },
          { label: isEdit ? 'workflow.edit_tpl' : 'workflow.create_tpl' },
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
        {params.step === 'basic' && <StepOneBasic isEdit={isEdit} isHydrated={isHydrated} />}
        {params.step === 'jobs' && <StepTwoJobs isEdit={isEdit} />}
      </FormArea>
    </>
  );
};

export default TemplateForm;
