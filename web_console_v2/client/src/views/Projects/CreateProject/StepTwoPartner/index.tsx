import React, { FC, useEffect } from 'react';
import { useHistory } from 'react-router';
import { ProjectTaskType } from 'typings/project';
import { useRecoilState } from 'recoil';
import { projectCreateForm, ProjectCreateForm } from 'stores/project';
import { Button, Form } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import ActionRules from './ActionRules';

import styles from './index.module.less';

const StepTwoPartner: FC<{
  onFormValuesChange?: () => void;
}> = () => {
  const history = useHistory();
  const [form] = Form.useForm();
  const [projectForm, setProjectForm] = useRecoilState<ProjectCreateForm>(projectCreateForm);

  useEffect(() => {
    if (!projectForm.config.abilities || !projectForm.name) {
      history.push('/projects/create/config');
    }
  });

  return (
    <div className={styles.container}>
      <div>
        <Form form={form} initialValues={projectForm} onSubmit={goStepThree} layout="vertical">
          <ActionRules taskType={projectForm.config.abilities?.[0] as ProjectTaskType} />
          <Form.Item>
            <GridRow className={styles.btn_container} gap={10} justify="center">
              <Button className={styles.btn_content} type="primary" htmlType="submit">
                下一步
              </Button>

              <Button onClick={() => history.goBack()}>上一步</Button>
            </GridRow>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
  function goStepThree(values: any) {
    setProjectForm({
      ...projectForm,
      config: {
        ...projectForm.config,
        ...values.config,
      },
    });
    history.push(`/projects/create/partner`);
  }
};

export default StepTwoPartner;
