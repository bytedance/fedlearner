import React, { ReactElement, useEffect, useState } from 'react';
import { useUnmount } from 'react-use';
import { Redirect, Route, useHistory, useParams } from 'react-router';
import { useResetCreateForm } from 'hooks/project';
import { createPendingProject } from 'services/project';

import { Message as message, Grid, Steps } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import BackButton from 'components/BackButton';
import StepOneConfig from './StepOneConfig';
import StepTwoPartner from './StepTwoPartner';
import StepThreeAuthorize from './StepThreeAuthorize';

import styles from './index.module.less';

const { Step } = Steps;
const { Row } = Grid;

enum CreateSteps {
  config,
  authorize,
  partner,
}

function CreateProject(): ReactElement {
  const history = useHistory();
  const { step } = useParams<{ step: keyof typeof CreateSteps | undefined }>();
  const [currentStep, setStep] = useState(CreateSteps[step || 'config']);
  const [isFormValueChanged, setIsFormValueChanged] = useState(false);

  const reset = useResetCreateForm();

  useUnmount(() => {
    reset();
  });

  useEffect(() => {
    setStep(CreateSteps[step || 'config']);
  }, [step]);

  if (!step) {
    return <Redirect to={`/projects/create/config`} />;
  }

  return (
    <div className={styles.container}>
      <SharedPageLayout
        title={
          <BackButton
            onClick={() => history.replace('/projects')}
            isShowConfirmModal={isFormValueChanged}
          >
            工作区管理
          </BackButton>
        }
        centerTitle="创建工作区"
      >
        <Row justify="center">
          <div className={styles.step_container}>
            <Steps
              current={currentStep + 1}
              style={{ maxWidth: 780, margin: '0 auto' }}
              size="small"
            >
              <Step title="全局配置" />
              <Step title="本方授权策略" />
              <Step title="邀请合作伙伴" />
            </Steps>
          </div>
        </Row>
        <section className={styles.form_area}>
          <Route
            path={`/projects/create/config`}
            exact
            render={() => <StepOneConfig onFormValueChange={onFormValueChange} />}
          />
          <Route path={'/projects/create/authorize'} exact render={() => <StepTwoPartner />} />
          <Route
            path={`/projects/create/partner`}
            exact
            render={() => <StepThreeAuthorize onSubmit={onSubmit} />}
          />
        </section>
      </SharedPageLayout>
    </div>
  );
  async function onSubmit(payload: any) {
    try {
      await createPendingProject(payload);
      message.success('创建成功！');
      history.push('/projects?project_list_type=pending');
    } catch (error: any) {
      message.error(error.message);
    }
  }
  function onFormValueChange() {
    if (!isFormValueChanged) {
      setIsFormValueChanged(true);
    }
  }
}

export default CreateProject;
