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
import { buildFormSchemaFromJob } from 'shared/formSchema';
import VariableSchemaForm, { formActions } from 'components/VariableSchemaForm';
import { FormilySchema } from 'typings/formily';
import GridRow from 'components/_base/GridRow';
import VariablePermission from 'components/VariblePermission';
import { useStoreActions, useStoreState } from 'react-flow-renderer';
import { DrawerProps } from 'antd/lib/drawer';
import {
  getNodeIdByJob,
  GlobalConfigNode,
  JobNode,
  JobNodeStatus,
} from 'components/WorkflowJobsFlowChart/helpers';
import { updateNodeStatusById } from 'components/WorkflowJobsFlowChart';
import { cloneDeep } from 'lodash';
import { useRecoilState } from 'recoil';
import { workflowConfigForm } from 'stores/workflow';
import { IFormState } from '@formily/antd';
import { giveWeakRandomKey, to } from 'shared/helpers';
import { useTranslation } from 'react-i18next';
import { removeUndefined } from 'shared/object';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Eye } from 'components/IconPark';
import { WorkflowConfig } from 'typings/workflow';

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
  node: JobNode | GlobalConfigNode;
  toggleVisible?: Function;
  onConfirm: Function;
  onViewPeerConfigClick: (...args: any[]) => void;
  isAccept?: boolean;
}
export type JobFormDrawerExposedRef = {
  validateCurrentJobForm(): Promise<boolean>;
  saveCurrentValues(): void;
  getCurrentNodeID(): string | undefined;
};

const JobFormDrawer: ForwardRefRenderFunction<JobFormDrawerExposedRef, Props> = (
  { node, toggleVisible, onConfirm, isAccept, onViewPeerConfigClick, ...props },
  parentRef,
) => {
  const { t } = useTranslation();
  const [randomKey, setRandomKey] = useState<string>(giveWeakRandomKey());
  const setSelectedElements = useStoreActions((actions) => actions.setSelectedElements);
  const [formSchema, setFormSchema] = useState<FormilySchema>(null as any);
  const jobNodes = useStoreState((store) => store.nodes);
  // Current workflow config value on store
  const [workflowConfig, setWorkflowConfigData] = useRecoilState(workflowConfigForm);

  useEffect(() => {
    if (node?.data) {
      setRandomKey(giveWeakRandomKey());
      // prop 'node' is from `templateInUsing` which only has job definition
      // in order to hydrate the Form, we need get user-inputs (whick storing on `workflowConfigForm`)
      // and merge the yser-inputs to definition
      const jobDataMergedWithValue = _mergeDefsWithValues(node, workflowConfig);
      const schema = buildFormSchemaFromJob(jobDataMergedWithValue);
      setFormSchema(schema);
    }
  }, [node, workflowConfig]);

  useImperativeHandle(parentRef, () => {
    return {
      validateCurrentJobForm: validateCurrentForm,
      saveCurrentValues: saveCurrentValuesToRecoil,
      getCurrentNodeID: () => data?.raw.name,
    };
  });

  const data = node?.data;

  if (!data) {
    return null;
  }

  const currentJobIdx = data.index;
  const currentJobIdxDisplay = currentJobIdx + 1;
  const isFinalStep = currentJobIdxDisplay === jobNodes.length;
  const confirmButtonText = isFinalStep
    ? t('workflow.btn_conf_done')
    : t('workflow.btn_conf_next_step', { current: currentJobIdxDisplay, total: jobNodes.length });

  return (
    <ErrorBoundary>
      <Container
        getContainer="#app-content"
        mask={false}
        width="640px"
        onClose={closeDrawer}
        headerStyle={{ display: 'none' }}
        {...props}
      >
        <DrawerHeader align="middle" justify="space-between">
          <DrawerTitle>{data.raw.name}</DrawerTitle>
          <GridRow gap="10">
            {isAccept && (
              <Button size="small" icon={<Eye />} onClick={onViewPeerConfigClick}>
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

  function deselectAllNode() {
    setSelectedElements([]);
  }
  async function validateCurrentForm(): Promise<boolean> {
    // When no Node opened yet
    if (!data) return true;

    const nodeId = getNodeIdByJob(data.raw);
    const { Warning, Success } = JobNodeStatus;
    const [_, error] = await to(formActions.validate());

    // Update job node status to validation result
    updateNodeStatusById({
      id: nodeId,
      status: error ? Warning : Success,
    });

    return !error;
  }
  function closeDrawer() {
    saveCurrentValuesToRecoil();
    // validate current form and tag corresponding Node status
    validateCurrentForm();
    toggleVisible && toggleVisible(false);
    deselectAllNode();
  }
  async function confirmAndGoNextJob() {
    if (isFinalStep) {
      return closeDrawer();
    }
    const valid = await validateCurrentForm();
    saveCurrentValuesToRecoil();

    if (!valid) return;
    const nextNodeToSelect = jobNodes.find((node) => node.data.index === currentJobIdx + 1);

    if (nextNodeToSelect) {
      setSelectedElements([nextNodeToSelect]);
      // Tell parent component that need to point next job
      onConfirm && onConfirm(nextNodeToSelect);
    }
  }
  /**
   * Write current form values to workflowConfigForm on recoil
   */
  function saveCurrentValuesToRecoil(): Promise<void> {
    return new Promise((resolve) => {
      formActions.getFormState((state: IFormState) => {
        const values = removeUndefined(state.values);
        const { variables, job_definitions, ...others } = workflowConfig;

        // If it's global config node
        if (node.type === 'global') {
          // NOTE: value from recoil is readonly
          const variablesCopy = cloneDeep(variables);

          setWorkflowConfigData({
            ...others,
            job_definitions,
            variables: variablesCopy?.map((item) => {
              return {
                ...item,
                value: values[item.name],
              };
            }),
          });
          return resolve();
        }

        // If normal job config node
        const jobsDefsCopy = cloneDeep(job_definitions);
        const targetJobDef = jobsDefsCopy.find(({ name }) => name === data?.raw.name);

        if (targetJobDef) {
          const targetJobIdx = jobsDefsCopy.findIndex(({ name }) => name === data?.raw.name);

          targetJobDef.variables = targetJobDef.variables.map((item) => {
            return {
              ...item,
              value: values[item.name],
            };
          });

          jobsDefsCopy[targetJobIdx] = targetJobDef;

          setWorkflowConfigData({
            ...others,
            variables,
            job_definitions: jobsDefsCopy,
          });
        }

        resolve();
      });
    });
  }
};

function _mergeDefsWithValues(node: JobNode | GlobalConfigNode, workflowConfig: WorkflowConfig) {
  if (node.type === 'global') {
    const copy = cloneDeep(node);
    workflowConfig.variables?.forEach((item) => {
      const target = copy.data.raw.variables.find((varDef) => varDef.name === item.name);
      if (target) {
        target.value = item.value;
      }
    });
    return copy.data.raw;
  }

  if (node.type === 'config') {
    const copy = cloneDeep(node);

    const theJob = workflowConfig.job_definitions.find((def) => def.name === node.data.raw.name);

    theJob?.variables.forEach((item) => {
      const target = copy.data.raw.variables.find((varDef) => varDef.name === item.name);
      if (target) {
        target.value = item.value;
      }
    });
    return copy.data.raw;
  }

  return node.data.raw as never;
}

export default forwardRef(JobFormDrawer);
