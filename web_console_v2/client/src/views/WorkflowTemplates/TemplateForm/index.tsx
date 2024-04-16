import React, { FC, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Steps, Row, Card } from 'antd';
import styled from 'styled-components';
import { useParams, useHistory } from 'react-router-dom';
import { useUnmount } from 'react-use';
import { useResetCreateForm } from 'hooks/template';
import StepOneBasic from './StepOneBasic';
import StepTwoJobs from './StepTwoJobs';
import { clearMap } from './store';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';

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
  const history = useHistory();
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
    <SharedPageLayout
      title={
        <BackButton onClick={() => history.goBack()}>{t('menu.label_workflow_tpl')}</BackButton>
      }
      contentWrapByCard={false}
    >
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
    </SharedPageLayout>
  );
};

export default TemplateForm;
