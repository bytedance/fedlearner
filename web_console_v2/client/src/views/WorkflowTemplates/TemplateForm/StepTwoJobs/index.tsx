import React, { FC, useState, useRef } from 'react';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { WORKFLOW_JOB_NODE_CHANNELS } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { AddJobPayload } from './TemplateConfigNode';
import WorkflowTemplateCanvas, { ExposedRef as CanVasExposedRef } from './TemplateCanvas';
import { isNode, ReactFlowProvider } from 'react-flow-renderer';
import { ChartNode, ChartNodeStatus } from 'components/WorkflowJobsCanvas/types';
import { useSubscribe } from 'hooks';
import { cloneDeep, last } from 'lodash';
import { useToggle } from 'react-use';
import { useRecoilState } from 'recoil';
import { giveWeakRandomKey, to } from 'shared/helpers';
import { templateForm } from 'stores/template';
import { Modal, Button, message } from 'antd';
import styled from 'styled-components';
import { Job, JobDefinitionForm, JobDependency } from 'typings/job';
import JobComposeDrawer, { ExposedRef as DrawerExposedRef } from './JobComposeDrawer';
import {
  getOrInsertValueById,
  TPL_GLOBAL_NODE_UUID,
  turnUuidDepToJobName,
  upsertValue,
  removeValueById,
} from '../store';
import { Redirect, useHistory, useParams } from 'react-router';
import { ExclamationCircle } from 'components/IconPark';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import { useTranslation } from 'react-i18next';
import GridRow from 'components/_base/GridRow';
import { WorkflowTemplatePayload } from 'typings/workflow';
import { createWorkflowTemplate, updateWorkflowTemplate } from 'services/workflow';
import { stringifyComplexDictField } from 'shared/formSchema';

const Container = styled.main`
  height: 100%;
`;

const ChartHeader = styled.header`
  height: 48px;
  padding: 13px 20px;
  font-size: 14px;
  line-height: 22px;
  background-color: white;
`;
const TemplateName = styled.h3`
  margin-bottom: 0;
`;
const Footer = styled.footer`
  position: sticky;
  bottom: 0;
  z-index: 5; // just > react-flow' z-index
  padding: 15px 36px;
  background-color: white;
`;

function _createASlimJobRawData({
  uuid,
  dependencies,
}: {
  uuid?: string;
  dependencies: JobDependency[];
}): any {
  return {
    uuid: uuid || giveWeakRandomKey(),
    dependencies: [...dependencies],
  };
}

const TemplateStepTowJobs: FC<{ isEdit?: boolean }> = ({ isEdit }) => {
  const history = useHistory();
  const { t } = useTranslation();
  const params = useParams<{ id?: string }>();

  const [drawerVisible, toggleDrawerVisible] = useToggle(false);

  const drawerRef = useRef<DrawerExposedRef>();
  const canvasRef = useRef<CanVasExposedRef>();

  const [submitting, setSubmitting] = useToggle(false);
  const [isGlobal, setIsGlobal] = useState(false);
  const [currNode, setCurrNode] = useState<ChartNode>();

  const [template, setTemplate] = useRecoilState(templateForm);

  useSubscribe(WORKFLOW_JOB_NODE_CHANNELS.click_add_job, (_: any, payload: AddJobPayload) => {
    const nextVal = cloneDeep(template);
    const jobDefs = nextVal.config.job_definitions;

    const { position, data, id } = payload;
    const rows = data.rows!;

    const rowIdx = rows?.findIndex((row) => row.find((col) => col.raw.uuid === id));
    const hasRowFollowed = Boolean(rows[rowIdx + 1]);

    const uuidOfLastJobInRow = last(rows[rowIdx])!.raw.uuid;
    const uuidOfHeadJobInRow = last(rows[rowIdx])!.raw.uuid;

    const leftPivotJobIdx = jobDefs.findIndex((item) => item.uuid === uuidOfHeadJobInRow);
    const rightPivotJobIdx = jobDefs.findIndex((item) => item.uuid === uuidOfLastJobInRow);

    const isInset2Left = position === 'left';
    const isInset2Bottom = position === 'bottom';

    const preJobs = jobDefs.slice(0, leftPivotJobIdx);
    const midJobs = jobDefs.slice(leftPivotJobIdx, rightPivotJobIdx + 1);
    const postJobs = jobDefs.slice(rightPivotJobIdx + 1, jobDefs.length);

    const newJobDeps: JobDependency[] = [];
    const newJobUuid = giveWeakRandomKey();

    if (isInset2Bottom) {
      const depRow = rows[rowIdx];
      newJobDeps.push(...depRow.map((col: any) => ({ source: col.raw.uuid })));

      if (hasRowFollowed) {
        const followedRow = rows[rowIdx + 1];

        followedRow.forEach((col) => {
          const def = jobDefs.find((def) => def.uuid === col.raw.uuid);
          if (def) {
            def.dependencies = [{ source: newJobUuid }];
          }
        });
      }
    } else {
      const depRow = rows[rowIdx - 1];
      newJobDeps.push(...depRow.map((col: any) => ({ source: col.raw.uuid })));
    }

    const newJob = _createASlimJobRawData({ uuid: newJobUuid, dependencies: newJobDeps });

    // If insert to right or bottom, before should be empty
    const before = [isInset2Left && newJob].filter(Boolean);
    // If insert to left, after should be empty
    const after = [!isInset2Left && newJob].filter(Boolean);

    nextVal.config.job_definitions = [...preJobs, ...before, ...midJobs, ...after, ...postJobs];

    setTemplate(nextVal);
  });

  if (!template?.name) {
    if (isEdit) {
      return <Redirect to={`/workflow-templates/edit/basic/${params.id}`} />;
    }
    return <Redirect to={'/workflow-templates/create/basic'} />;
  }

  return (
    <ErrorBoundary>
      <Container>
        <ChartHeader>
          <TemplateName>{template.name}</TemplateName>
        </ChartHeader>

        <ReactFlowProvider>
          <WorkflowTemplateCanvas
            ref={canvasRef as any}
            isEdit={isEdit}
            template={template}
            onNodeClick={onNodeClick}
            onCanvasClick={onCanvasClick}
          />
        </ReactFlowProvider>

        <JobComposeDrawer
          ref={drawerRef as any}
          isGlobal={isGlobal}
          uuid={currNode?.id}
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          onSubmit={onDrawerFormSubmit}
          onClose={onCloseDrawer}
          onDelete={onDeleteJob}
        />

        <Footer>
          <GridRow gap="12">
            <Button type="primary" loading={submitting} onClick={onSubmitClick}>
              {t('submit')}
            </Button>
            <Button onClick={onPrevStepClick} disabled={submitting}>
              {t('previous_step')}
            </Button>
            <Button onClick={onCancelForkClick} disabled={submitting}>
              {t('cancel')}
            </Button>
          </GridRow>
        </Footer>
      </Container>
    </ErrorBoundary>
  );

  // ---------------- Methods --------------------

  function checkIfAllJobConfigCompleted() {
    const isAllCompleted = canvasRef.current?.chartInstance
      .getElements()
      .filter(isNode)
      .every((node) => {
        return node.data.status === ChartNodeStatus.Success;
      });

    return isAllCompleted;
  }
  function saveCurrentValues(values?: JobDefinitionForm) {
    if (currNode?.id) {
      upsertValue(currNode?.id, values || drawerRef.current?.getFormValues());
    }
  }
  async function validateCurrentForm() {
    if (currNode?.id) {
      const valid = await drawerRef.current?.validate();
      canvasRef.current?.updateNodeStatusById({
        id: currNode?.id,
        status: valid ? ChartNodeStatus.Success : ChartNodeStatus.Warning,
      });

      // drawerRef.current?.reset();
    }
  }

  // ---------------- Handlers --------------------

  function onPrevStepClick() {
    history.goBack();
  }
  function onDeleteJob() {
    const uuid = currNode?.id;

    if (uuid) {
      const nextVal = cloneDeep(template);
      const jobDefs = nextVal.config.job_definitions;
      const idx = jobDefs.findIndex((def) => def.uuid === uuid);
      const jobDefToRemove = jobDefs[idx];

      for (let i = idx + 1; i < jobDefs.length; i++) {
        const def = jobDefs[i];

        if (def.dependencies.some((dep) => dep.source === uuid)) {
          def.dependencies = def.dependencies
            .filter((dep) => dep.source !== uuid)
            .concat(jobDefToRemove.dependencies);
        }
      }

      nextVal.config.job_definitions = [
        ...jobDefs.slice(0, idx),
        ...jobDefs.slice(idx + 1, jobDefs.length),
      ];
      setTemplate(nextVal);
      // Remove job from store
      removeValueById(uuid);
      setCurrNode(null as any);
      toggleDrawerVisible(false);
    }
  }
  function onCancelForkClick() {
    Modal.confirm({
      title: t('workflow.msg_sure_2_cancel_tpl'),
      icon: <ExclamationCircle />,
      zIndex: Z_INDEX_GREATER_THAN_HEADER,
      content: t('workflow.msg_will_drop_tpl_config'),
      style: {
        top: '30%',
      },
      onOk() {
        history.push('/workflow-templates');
      },
    });
  }
  function onDrawerFormSubmit(values: JobDefinitionForm) {
    saveCurrentValues(values);

    canvasRef.current?.updateNodeStatusById({
      id: currNode?.id!,
      status: ChartNodeStatus.Success,
    });

    canvasRef.current?.setSelectedNodes([]);
  }
  async function onCloseDrawer() {
    canvasRef.current?.setSelectedNodes([]);
    await validateCurrentForm();
  }
  async function onNodeClick(nextNode: ChartNode) {
    saveCurrentValues();
    await validateCurrentForm();

    drawerRef.current?.reset();

    setCurrNode(nextNode);

    canvasRef.current?.updateNodeStatusById({
      id: nextNode?.id!,
      status: ChartNodeStatus.Processing,
    });

    setIsGlobal(!!nextNode?.data.isGlobal);
    toggleDrawerVisible(true);
  }
  async function onCanvasClick() {
    saveCurrentValues();
    await validateCurrentForm();

    drawerRef.current?.reset();

    toggleDrawerVisible(false);
    setCurrNode(null as any);
  }
  async function onSubmitClick() {
    if (!checkIfAllJobConfigCompleted()) {
      return message.warn(t('workflow.msg_config_unfinished'));
    }

    toggleDrawerVisible(false);
    setSubmitting(true);

    const { config, ...basics } = cloneDeep(template);
    let payload: WorkflowTemplatePayload = { ...basics, config: {} as any };

    payload.config.variables = getOrInsertValueById(TPL_GLOBAL_NODE_UUID)?.variables!;

    payload.config.job_definitions = config.job_definitions.map((item) => {
      const values = getOrInsertValueById(item.uuid);
      return {
        ...values,
        dependencies: item.dependencies.map(turnUuidDepToJobName),
      } as Job;
    });

    payload.config.group_alias = basics.group_alias;
    payload.config.is_left = basics.is_left || false;

    payload = stringifyComplexDictField(payload);

    const [, error] = await to(
      isEdit ? updateWorkflowTemplate(params.id!, payload) : createWorkflowTemplate(payload),
    );

    if (error) {
      setSubmitting(false);
      return message.error(error.message);
    }
    message.success(isEdit ? '模板修改成功!' : '模板创建成功！');
    history.push('/workflow-templates');
  }
};

export default TemplateStepTowJobs;
