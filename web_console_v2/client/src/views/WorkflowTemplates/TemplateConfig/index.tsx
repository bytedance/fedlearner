import React, { FC, useCallback, useRef, useState } from 'react';
import { Button, Message, Tooltip } from '@arco-design/web-react';
import Modal from 'components/Modal';
import ErrorBoundary from 'components/ErrorBoundary';
import { WORKFLOW_JOB_NODE_CHANNELS } from 'components/WorkflowJobsCanvas/JobNodes/shared';
import { ChartNode, ChartNodeStatus } from 'components/WorkflowJobsCanvas/types';
import GridRow from 'components/_base/GridRow';
import { useSubscribe } from 'hooks';
import { cloneDeep, last } from 'lodash-es';
import { isNode, ReactFlowProvider } from 'react-flow-renderer';
import { Redirect, useHistory, useParams } from 'react-router';
import { useToggle } from 'react-use';
import { useRecoilState } from 'recoil';
import {
  createTemplateRevision,
  createWorkflowTemplate,
  updateWorkflowTemplate,
} from 'services/workflow';
import { stringifyComplexDictField } from 'shared/formSchema';
import { giveWeakRandomKey, nextTick, to } from 'shared/helpers';
import { templateForm } from 'stores/template';
import styled from './index.module.less';
import { JobDependency } from 'typings/job';
import {
  JobSlotReferenceType,
  WorkflowTemplatePayload,
  WorkflowTemplateType,
} from 'typings/workflow';
import {
  definitionsStore,
  editorInfosStore,
  JobDefinitionForm,
  mapUuidDepToJobName,
  TPL_GLOBAL_NODE_UUID,
  VariableDefinitionForm,
} from 'views/WorkflowTemplates/TemplateForm/stores';
import JobComposeDrawer, {
  COMPOSE_DRAWER_CHANNELS,
  ExposedRef as DrawerExposedRef,
  InspectPayload,
  scrollDrawerBodyTo,
} from './JobComposeDrawer';
import {
  parseJobPropRef,
  parseOtherJobRef,
  parseSelfRef,
  parseWorkflowRef,
} from './JobComposeDrawer/SloEntrytList/helpers';
import WorkflowTemplateCanvas, { ExposedRef as CanVasExposedRef } from './TemplateCanvas';
import { AddJobPayload } from './TemplateConfigNode';
import { useGetIsCanEditTemplate } from 'views/WorkflowTemplates/shared';

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

const TemplateConifg: FC<{
  isEdit?: boolean;
  isCheck?: boolean;
  revisionId?: number;
}> = ({ isEdit, isCheck, revisionId }) => {
  const history = useHistory();
  const params = useParams<{ id?: string; revision_id?: string }>();

  const [drawerVisible, toggleDrawerVisible] = useToggle(false);

  const drawerRef = useRef<DrawerExposedRef>();
  const canvasRef = useRef<CanVasExposedRef>();

  const rePositionChart = useRef(false);

  const [submitting, setSubmitting] = useToggle(false);
  /** Whether is workflow gloabl variables node */
  const [isGlobal, setIsGlobal] = useState(false);
  const [prevNode, setPrevNode] = useState<ChartNode | undefined>();
  const [currNode, setCurrNode] = useState<ChartNode>();

  const [template, setTemplate] = useRecoilState(templateForm);

  const { isCanEdit, tip } = useGetIsCanEditTemplate(
    template.kind === WorkflowTemplateType.BUILT_IN,
  );
  /** updateTemplate only isEdit is true
   * createTemplate when status is isCreate || isRevision || revisionId !== undefined
   */
  const isRevision = Boolean(params.revision_id);

  const onDrawerFormSubmit = useCallback(
    (values: JobDefinitionForm) => {
      saveCurrentValues({ values, isGlobal });

      canvasRef.current?.updateNodeStatusById({
        id: currNode?.id!,
        status: ChartNodeStatus.Success,
      });

      canvasRef.current?.setSelectedNodes([]);
      setCurrNode(undefined);
      setPrevNode(undefined);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currNode, isGlobal],
  );

  const onSubmitClick = useCallback(async () => {
    if (!checkIfAllJobConfigCompleted()) {
      return Message.warning('未完成配置或有正在编辑的任务，请确认后再次提交');
    }
    toggleDrawerVisible(false);
    setSubmitting(true);

    const { config, ...basics } = cloneDeep(template);
    let payload: WorkflowTemplatePayload<JobDefinitionForm, VariableDefinitionForm> = {
      ...basics,
      config: {} as any,
    };

    payload.config.variables = cloneDeep(
      definitionsStore.getValueById(TPL_GLOBAL_NODE_UUID)?.variables!,
    );

    payload.config.job_definitions = config.job_definitions.map((item) => {
      const values = cloneDeep(definitionsStore.getValueById(item.uuid));
      return {
        ...values,
        dependencies: item.dependencies.map(mapUuidDepToJobName),
      } as any;
    });
    payload.editor_info = {
      yaml_editor_infos: Object.fromEntries(
        /**
         * Convert job & variable uuid in reference to job & variable's name
         */
        config.job_definitions.map((item) => {
          const { name: selfName, variables: selfVars } = definitionsStore.getValueById(item.uuid)!;
          const { slotEntries, meta_yaml } = cloneDeep(editorInfosStore.getValueById(item.uuid)!);
          slotEntries.forEach(([_, slot]) => {
            if (slot.reference_type === JobSlotReferenceType.OTHER_JOB) {
              const [jobUuid, varUuid] = parseOtherJobRef(slot.reference);
              const target = definitionsStore.getValueById(jobUuid);

              if (target) {
                slot.reference = slot.reference
                  .replace(jobUuid, target.name)
                  .replace(varUuid, target.variables.find((item) => item._uuid === varUuid)?.name!);
              }
            }

            if (slot.reference_type === JobSlotReferenceType.SELF) {
              const varUuid = parseSelfRef(slot.reference);

              slot.reference = slot.reference.replace(
                varUuid,
                selfVars.find((item) => item._uuid === varUuid)?.name!,
              );
            }

            if (slot.reference_type === JobSlotReferenceType.JOB_PROPERTY) {
              const [jobUuid] = parseJobPropRef(slot.reference);
              const target = definitionsStore.getValueById(jobUuid);

              if (target) {
                slot.reference = slot.reference.replace(jobUuid, target.name);
              }
            }

            if (slot.reference_type === JobSlotReferenceType.WORKFLOW) {
              const varUuid = parseWorkflowRef(slot.reference);
              const globalDef = definitionsStore.getValueById(TPL_GLOBAL_NODE_UUID)!;
              slot.reference = slot.reference.replace(
                varUuid,
                globalDef.variables.find((item) => item._uuid === varUuid)?.name!,
              );
            }
          });

          return [selfName, { meta_yaml, slots: Object.fromEntries(slotEntries) }];
        }),
      ),
    };

    // === Remove variables' _uuid start ===
    payload.config.variables.forEach((item: Partial<VariableDefinitionForm>) => {
      if (item._uuid) delete item._uuid;
    });
    payload.config.job_definitions.forEach((job) => {
      job.variables.forEach((variable: Partial<VariableDefinitionForm>) => {
        if (variable._uuid) delete variable._uuid;
      });
    });
    // === Remove variables' _uuid end ===

    payload.config.group_alias = basics.group_alias;

    payload = stringifyComplexDictField(payload);

    const [res, error] = await to(
      isEdit && !revisionId && !isRevision
        ? updateWorkflowTemplate(params.id!, payload)
        : createWorkflowTemplate(payload),
    );
    if (error) {
      setSubmitting(false);
      return Message.error(error.message);
    }

    if (isEdit && !revisionId && !isRevision) {
      await to(createTemplateRevision(params.id!));
    } else {
      await to(createTemplateRevision(res.data.id));
    }

    Message.success(isEdit ? '模板修改成功!' : '模板创建成功！');

    if (isEdit && !revisionId && !isRevision) {
      history.push(`/workflow-center/workflow-templates/detail/${params.id}/config`);
    } else {
      history.push(`/workflow-center/workflow-templates`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template]);

  useSubscribe(
    WORKFLOW_JOB_NODE_CHANNELS.click_add_job,
    (_: any, payload: AddJobPayload) => {
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

      const isInsert2Left = position === 'left';
      const isInsert2Bottom = position === 'bottom';

      const preJobs = jobDefs.slice(0, leftPivotJobIdx);
      const midJobs = jobDefs.slice(leftPivotJobIdx, rightPivotJobIdx + 1);
      const postJobs = jobDefs.slice(rightPivotJobIdx + 1, jobDefs.length);

      const newJobDeps: JobDependency[] = [];
      const newJobUuid = giveWeakRandomKey();

      if (isInsert2Bottom) {
        const depRow = rows[rowIdx];
        newJobDeps.push(...depRow.map((col: any) => ({ source: col.raw.uuid })));

        if (hasRowFollowed) {
          const followedRow = rows[rowIdx + 1];
          // New job will create new row that only contain the new job
          followedRow.forEach((col) => {
            const def = jobDefs.find((def) => def.uuid === col.raw.uuid);
            if (def) {
              def.dependencies = [{ source: newJobUuid }];
            }
          });
        }
      } else {
        const depRow = rows[rowIdx - 1];

        // New job add all depRow's job dependencies
        if (depRow && depRow.every((item) => !item.isGlobal)) {
          newJobDeps.push(...depRow.map((col: any) => ({ source: col.raw.uuid })));
        }

        // New job will be added by each followedRow's job dependencies
        if (hasRowFollowed) {
          const followedRow = rows[rowIdx + 1];
          followedRow.forEach((col) => {
            const def = jobDefs.find((def) => def.uuid === col.raw.uuid);
            if (def) {
              def.dependencies = def.dependencies.concat([{ source: newJobUuid }]);
            }
          });
        }
      }

      const newJob = _createASlimJobRawData({ uuid: newJobUuid, dependencies: newJobDeps });

      // If insert to right or bottom, before should be empty
      const before = [isInsert2Left && newJob].filter(Boolean);
      // If insert to left, after should be empty
      const after = [!isInsert2Left && newJob].filter(Boolean);

      nextVal.config.job_definitions = [...preJobs, ...before, ...midJobs, ...after, ...postJobs];

      setTemplate(nextVal);
    },
    [template.config.job_definitions.length],
  );
  useSubscribe(
    COMPOSE_DRAWER_CHANNELS.inspect,
    (_: string, { jobUuid }: InspectPayload) => {
      // Is current job`
      if (jobUuid === currNode?.id || !jobUuid) return;

      inspectNode(jobUuid);
    },
    // Need to refresh currNode ref inside inspectNode>selectNode each time,
    // otherwise, currNode will be undefined
    [currNode?.id],
  );
  if (!template?.name) {
    if (isEdit) {
      return <Redirect to={`/workflow-center/workflow-templates/edit/basic/${params.id}`} />;
    }
    return <Redirect to={'/workflow-center/workflow-templates/create/basic'} />;
  }

  return (
    <ErrorBoundary>
      <main className={styled.container}>
        {isCheck ? (
          <></>
        ) : (
          <header className={styled.chart_header}>
            <h3 className={styled.template_name}>{template.name}</h3>
          </header>
        )}
        <ReactFlowProvider>
          <WorkflowTemplateCanvas
            ref={canvasRef as any}
            isEdit={isEdit}
            isCheck={isCheck}
            template={template}
            onNodeClick={selectNode}
            onCanvasClick={onCanvasClick}
          />
        </ReactFlowProvider>

        <JobComposeDrawer
          ref={drawerRef as any}
          isGlobal={isGlobal}
          isCheck={isCheck}
          revisionId={revisionId}
          uuid={currNode?.id}
          prevNode={prevNode}
          visible={drawerVisible}
          toggleVisible={toggleDrawerVisible}
          onSubmit={onDrawerFormSubmit}
          onClose={onCloseDrawer}
          onDelete={onDeleteJob}
          onBack={onBackToPrevJob}
        />

        {isCheck ? (
          <></>
        ) : (
          <footer className={styled.footer}>
            <GridRow gap="12">
              <Tooltip content={tip}>
                <Button
                  type="primary"
                  loading={submitting}
                  onClick={onSubmitClick}
                  disabled={!isCanEdit}
                >
                  确认
                </Button>
              </Tooltip>
              <Button onClick={onPrevStepClick} disabled={submitting}>
                上一步
              </Button>
              <Button onClick={onCancelForkClick} disabled={submitting}>
                取消
              </Button>
            </GridRow>
          </footer>
        )}
      </main>
    </ErrorBoundary>
  );

  // ---------------- Methods --------------------

  function saveCurrentValues(payload: { values?: JobDefinitionForm; isGlobal: boolean }) {
    const currUuid = currNode?.id;
    if (currUuid) {
      const { _slotEntries: slotEntries, ...definitionValues } =
        payload.values ?? drawerRef.current?.getFormValues()!;

      const editInfo = editorInfosStore.getValueById(currUuid);

      if (drawerRef.current?.isEasyMode && !payload.isGlobal && editInfo) {
        const { meta_yaml } = editInfo;
        editorInfosStore.upsertValue(currUuid, { slotEntries, meta_yaml });
      }

      definitionsStore.upsertValue(currUuid, definitionValues);
    }
  }
  function checkIfAllJobConfigCompleted() {
    const isAllCompleted = canvasRef.current?.chartInstance
      .getElements()
      .filter(isNode)
      .every((node) => {
        return node.data.status === ChartNodeStatus.Success;
      });

    return isAllCompleted;
  }

  async function validateCurrentForm(nodeId?: string) {
    const id = nodeId ?? currNode?.id;
    if (id) {
      canvasRef.current?.updateNodeStatusById({
        id,
        status: ChartNodeStatus.Validating,
      });
      const valid = await drawerRef.current?.validate();
      canvasRef.current?.updateNodeStatusById({
        id,
        status: valid ? ChartNodeStatus.Success : ChartNodeStatus.Error,
      });
    }
  }
  function inspectNode(uuid: string) {
    const targetJobNode = canvasRef.current?.chartInstance
      .getElements()
      .filter(isNode)
      .find((node) => {
        return node.id === uuid;
      });

    if (targetJobNode && canvasRef.current) {
      selectNode(targetJobNode as ChartNode);
      canvasRef.current.setSelectedNodes([targetJobNode]);
    }
  }
  async function selectNode(nextNode: ChartNode) {
    if (nextNode.id === currNode?.id) return;

    if (currNode) {
      setPrevNode(currNode);
    }

    saveCurrentValues({ isGlobal });
    validateCurrentForm(currNode?.id).then(() => {
      drawerRef.current?.reset();
      setCurrNode(nextNode);
      setIsGlobal(!!nextNode?.data.isGlobal);
    });

    canvasRef.current?.updateNodeStatusById({
      id: nextNode?.id!,
      status: ChartNodeStatus.Processing,
    });

    scrollDrawerBodyTo(0);

    toggleDrawerVisible(true);

    if (!drawerVisible && !rePositionChart.current) {
      // Put whole chart at left side due to the opened drawer will override it,
      // And we only do it once then let the user control it
      canvasRef.current?.chartInstance.setTransform({ x: 50, y: 50, zoom: 1 });
      rePositionChart.current = true;
    }
  }

  // ---------------- Handlers --------------------

  function onBackToPrevJob() {
    if (prevNode) {
      inspectNode(prevNode?.id);

      nextTick(() => {
        setPrevNode(undefined);
      });
    }
  }
  function onPrevStepClick() {
    history.goBack();
  }
  function onDeleteJob() {
    const uuid = currNode?.id;

    if (definitionsStore.size === 2) {
      Message.warning('工作流至少需要一个任务');
      return;
    }

    if (uuid) {
      const nextVal = cloneDeep(template);
      const jobDefs = nextVal.config.job_definitions;
      const idx = jobDefs.findIndex((def) => def.uuid === uuid);
      const jobDefToRemove = jobDefs[idx];

      const rows = currNode?.data.rows ?? [];
      const currNodeRowIdx = rows?.findIndex((row) => row.find((col) => col.raw.uuid === uuid));
      // If row that only contain currNode, so this row will be delete soon
      const shouldDeleteRow = rows[currNodeRowIdx].length === 1;

      for (let i = idx + 1; i < jobDefs.length; i++) {
        const def = jobDefs[i];
        // Find followedRow job
        if (def.dependencies.some((dep) => dep.source === uuid)) {
          // Each followedRow job dependencies remove jobDefToRemove
          def.dependencies = def.dependencies.filter((dep) => dep.source !== uuid);

          // If will delete row that only contain currNode, so each followedRow job dependencies add jobDefToRemove.dependencies
          if (shouldDeleteRow) {
            def.dependencies = def.dependencies.concat(jobDefToRemove.dependencies);
          }
        }
      }

      nextVal.config.job_definitions = [
        ...jobDefs.slice(0, idx),
        ...jobDefs.slice(idx + 1, jobDefs.length),
      ];
      setTemplate(nextVal);

      // Remove job from store
      // definitionsStore.removeValueById(uuid);
      definitionsStore.map.delete(uuid);
      editorInfosStore.removeValueById(uuid);

      setCurrNode(null as any);
      toggleDrawerVisible(false);
    }
  }
  function onCancelForkClick() {
    Modal.confirm({
      title: '确认取消编辑模板吗？',
      content: '取消后，已配置的模板内容将不再保留',
      onOk() {
        history.push(`/workflow-center/workflow-templates`);
      },
    });
  }

  async function onCloseDrawer() {
    canvasRef.current?.setSelectedNodes([]);
    validateCurrentForm(currNode?.id);
    setPrevNode(undefined);
  }

  async function onCanvasClick() {
    // If current job form is validating
    if (drawerRef.current?.isValidating) {
      return;
    }
    saveCurrentValues({ isGlobal });

    validateCurrentForm(currNode?.id).then(() => {
      drawerRef.current?.reset();
      setCurrNode(undefined);
      nextTick(() => {
        toggleDrawerVisible(false);
      });
    });

    setPrevNode(undefined);
  }
};

export default TemplateConifg;
