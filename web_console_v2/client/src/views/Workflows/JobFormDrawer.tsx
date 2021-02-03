import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useState,
  ForwardRefRenderFunction,
} from 'react';
import styled from 'styled-components';
import { CloseOutlined } from '@ant-design/icons';
import { Drawer, Row, Button } from 'antd';
import { buildFormSchemaFromJobDef } from 'shared/formSchema';
import VariableSchemaForm, { formActions } from 'components/VariableSchemaForm';
import { FormilySchema } from 'typings/formily';
import GridRow from 'components/_base/GridRow';
import VariablePermission from 'components/VariblePermission';
import { DrawerProps } from 'antd/lib/drawer';
import {
  getNodeIdByJob,
  ChartNode,
  JobNode,
  JobNodeStatus,
  NodeDataRaw,
} from 'components/WorkflowJobsFlowChart/helpers';
import { updateNodeStatusById } from 'components/WorkflowJobsFlowChart';
import { cloneDeep, Dictionary, noop } from 'lodash';
import { useRecoilState } from 'recoil';
import { workflowConfigForm } from 'stores/workflow';
import { IFormState } from '@formily/antd';
import { giveWeakRandomKey, to } from 'shared/helpers';
import { useTranslation } from 'react-i18next';
import { removeUndefined } from 'shared/object';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Eye } from 'components/IconPark';
import { Variable, WorkflowConfig } from 'typings/workflow';
import { Job } from 'typings/job';

const Container = styled(Drawer)`
  top: 60px;

  .ant-drawer-body {
    padding-top: 0;
  }
`;
const DrawerHeader = styled(Row)`
  height: 68px;
  margin: 0 -24px 0;
  padding-left: 24px;
  padding-right: 16px;
  border-bottom: 1px solid var(--darkGray9);
`;
const DrawerTitle = styled.h3`
  margin-bottom: 0;
`;
const PermissionDisplay = styled.div`
  margin: 0 -24px 42px;
  padding: 14px 24px;
  font-size: 12px;
  background-color: var(--gray1);
`;
const FormContainer = styled.div`
  padding-right: 68px;
  padding-bottom: 200px;
`;

interface Props extends DrawerProps {
  currentIdx?: number;
  nodesCount: number;
  jobDefinition?: NodeDataRaw;
  initialValues?: Variable[];
  toggleVisible?: Function;
  onGoNextJob: Function;
  onCloseDrawer: Function;
  onViewPeerConfigClick?: (...args: any[]) => void;
  showPeerConfigButton?: boolean;
}
export type JobFormDrawerExposedRef = {
  validateCurrentForm(): Promise<boolean>;
  getFormValues(): Promise<Dictionary<any>>;
};

const JobFormDrawer: ForwardRefRenderFunction<JobFormDrawerExposedRef, Props> = (
  {
    currentIdx,
    nodesCount,
    jobDefinition,
    initialValues,
    toggleVisible,
    onGoNextJob,
    showPeerConfigButton,
    onViewPeerConfigClick,
    onCloseDrawer,

    ...props
  },
  parentRef,
) => {
  const { t } = useTranslation();
  const [randomKey, setRandomKey] = useState<string>(giveWeakRandomKey());
  const [formSchema, setFormSchema] = useState<FormilySchema>(null as any);

  useEffect(() => {
    if (jobDefinition) {
      setRandomKey(giveWeakRandomKey());
      // prop 'node' is from `templateInUsing` which only has job definition
      // in order to hydrate the Form, we need get user-inputs (whick stored on `workflowConfigForm`)
      // and merge the user-inputs to definition
      const jobDefWithValues = _hydrate(jobDefinition, initialValues);
      const schema = buildFormSchemaFromJobDef(jobDefWithValues);
      setFormSchema(schema);
    }
  }, [jobDefinition, initialValues]);

  useImperativeHandle(parentRef, () => {
    return {
      validateCurrentForm: validateCurrentForm,
      getFormValues: getFormValues,
    };
  });

  if (!jobDefinition) {
    return null;
  }

  const currentJobIdxDisplay = (currentIdx || 0) + 1;
  const isFinalStep = currentJobIdxDisplay === nodesCount;
  const confirmButtonText = isFinalStep
    ? t('workflow.btn_conf_done')
    : t('workflow.btn_conf_next_step', {
        current: currentJobIdxDisplay,
        total: nodesCount || 0,
      });

  return (
    <ErrorBoundary>
      <Container
        {...props}
        getContainer="#app-content"
        mask={false}
        width="640px"
        headerStyle={{ display: 'none' }}
        onClose={closeDrawer}
      >
        <DrawerHeader align="middle" justify="space-between">
          <DrawerTitle>{jobDefinition.name}</DrawerTitle>
          <GridRow gap="10">
            {showPeerConfigButton && (
              <Button size="small" icon={<Eye />} onClick={onViewPeerConfigClick || noop}>
                {t('workflow.btn_see_peer_config')}
              </Button>
            )}
            <Button size="small" icon={<CloseOutlined />} onClick={closeDrawer} />
          </GridRow>
        </DrawerHeader>

        <PermissionDisplay>
          <GridRow gap="20">
            <label>{t('workflow.ptcpt_permission')}:</label>
            <VariablePermission.Writable desc />
            <VariablePermission.Readable desc />
            <VariablePermission.Private desc />
          </GridRow>
        </PermissionDisplay>

        {/* ☢️ Form Area */}
        <FormContainer>
          {formSchema && (
            <VariableSchemaForm
              key={randomKey}
              schema={formSchema}
              onConfirm={confirmAndGoNextJob}
              onCancel={closeDrawer as any}
              confirmText={confirmButtonText}
              cancelText={t('workflow.btn_close')}
            />
          )}
        </FormContainer>
      </Container>
    </ErrorBoundary>
  );

  async function validateCurrentForm(): Promise<boolean> {
    // When no Node opened yet
    if (!jobDefinition) return true;

    const nodeId = getNodeIdByJob(jobDefinition);
    const { Warning, Success } = JobNodeStatus;
    const [, error] = await to(formActions.validate());

    // Update job node status to validation result
    updateNodeStatusById({
      id: nodeId,
      status: error ? Warning : Success,
    });

    return !error;
  }
  function closeDrawer() {
    // validate current form and mark Node with corresponding status
    validateCurrentForm();
    toggleVisible && toggleVisible(false);
    onCloseDrawer();
  }
  async function confirmAndGoNextJob() {
    if (nodesCount === 0) return;

    const valid = await validateCurrentForm();

    if (!valid) return;

    if (isFinalStep) {
      return closeDrawer();
    }

    // Tell parent component that need to point next job
    onGoNextJob && onGoNextJob(jobDefinition);
  }

  function getFormValues(): Promise<Dictionary<any>> {
    return new Promise((resolve) => {
      formActions.getFormState((state: IFormState) => {
        resolve(removeUndefined(state.values));
      });
    });
  }
};

function _hydrate(jobDefinition: NodeDataRaw, varsWithValue?: Variable[]): Job {
  if (!varsWithValue) return jobDefinition;

  const jobDefCopy = cloneDeep(jobDefinition);

  jobDefCopy.variables.forEach((def) => {
    const value = varsWithValue.find((item) => item.name === def.name)?.value;

    if (value) {
      def.value = value;
    }
  });

  return jobDefCopy;
}

export default forwardRef(JobFormDrawer);
