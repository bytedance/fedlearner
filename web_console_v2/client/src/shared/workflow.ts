import {
  Workflow,
  WorkflowState,
  WorkflowExecutionDetails,
  WorkflowStateFilterParam,
  WorkflowStateFilterParamType,
} from 'typings/workflow';
import i18n from 'i18n';
import { StateTypes } from 'components/StateIndicator';
import { Job } from 'typings/job';

const {
  RUNNING,
  STOPPED,
  INVALID,
  COMPLETED,
  FAILED,
  PREPARE_RUN,
  PREPARE_STOP,
  WARMUP_UNDERHOOD,
  PENDING_ACCEPT,
  READY_TO_RUN,
  PARTICIPANT_CONFIGURING,
  UNKNOWN,
} = WorkflowState;

export const workflowStateFilterParamToStateTextMap: Record<
  WorkflowStateFilterParamType,
  string
> = {
  [WorkflowStateFilterParam.RUNNING]: i18n.t('workflow.state_running'),
  [WorkflowStateFilterParam.STOPPED]: i18n.t('workflow.state_stopped'),
  [WorkflowStateFilterParam.INVALID]: i18n.t('workflow.state_invalid'),
  [WorkflowStateFilterParam.COMPLETED]: i18n.t('workflow.state_success'),
  [WorkflowStateFilterParam.FAILED]: i18n.t('workflow.state_failed'),
  [WorkflowStateFilterParam.PREPARE_RUN]: i18n.t('workflow.state_prepare_run'),
  [WorkflowStateFilterParam.PREPARE_STOP]: i18n.t('workflow.state_prepare_stop'),
  [WorkflowStateFilterParam.WARMUP_UNDERHOOD]: i18n.t('workflow.state_warmup_underhood'),
  [WorkflowStateFilterParam.PENDING_ACCEPT]: i18n.t('workflow.state_pending_accept'),
  [WorkflowStateFilterParam.READY_TO_RUN]: i18n.t('workflow.state_ready_to_run'),
  [WorkflowStateFilterParam.PARTICIPANT_CONFIGURING]: i18n.t('workflow.state_configuring'),
  [WorkflowStateFilterParam.UNKNOWN]: i18n.t('workflow.state_unknown'),
};

const workflowStateFilterOrder = [
  WorkflowStateFilterParam.PENDING_ACCEPT,
  WorkflowStateFilterParam.READY_TO_RUN,
  WorkflowStateFilterParam.COMPLETED,
  WorkflowStateFilterParam.FAILED,
  WorkflowStateFilterParam.RUNNING,
  WorkflowStateFilterParam.STOPPED,
  WorkflowStateFilterParam.INVALID,
  WorkflowStateFilterParam.PARTICIPANT_CONFIGURING,
  WorkflowStateFilterParam.WARMUP_UNDERHOOD,
];
export const workflowStateOptionList = workflowStateFilterOrder.map((item) => ({
  label: workflowStateFilterParamToStateTextMap[item],
  value: item,
}));

// --------------- Xable judgement ----------------

export function isOperable(workflow: Workflow) {
  return [READY_TO_RUN, RUNNING, STOPPED, COMPLETED, FAILED].includes(workflow.state);
}

export function isForkable(workflow: Workflow) {
  const { forkable } = workflow;
  return forkable;
}

export function isEditable(workflow: Workflow) {
  const { state } = workflow;
  return [PARTICIPANT_CONFIGURING, READY_TO_RUN, STOPPED, COMPLETED, FAILED].includes(state);
}

// --------------- General stage getter ----------------

export function getWorkflowStage(workflow: Workflow): { type: StateTypes; text: string } {
  const { state } = workflow;

  switch (state) {
    case PARTICIPANT_CONFIGURING:
      return {
        text: i18n.t('workflow.state_configuring'),
        type: 'gold',
      };

    case PENDING_ACCEPT:
      return {
        text: i18n.t('workflow.state_pending_accept'),
        type: 'warning',
      };

    case WARMUP_UNDERHOOD:
      return {
        text: i18n.t('workflow.state_warmup_underhood'),
        type: 'warning',
      };

    case PREPARE_RUN:
      return {
        text: i18n.t('workflow.state_prepare_run'),
        type: 'warning',
      };

    case READY_TO_RUN:
      return {
        text: i18n.t('workflow.state_ready_to_run'),
        type: 'lime',
      };

    case RUNNING:
      return {
        text: i18n.t('workflow.state_running'),
        type: 'processing',
      };

    case PREPARE_STOP:
      return {
        text: i18n.t('workflow.state_prepare_stop'),
        type: 'error',
      };

    case STOPPED:
      return {
        text: i18n.t('workflow.state_stopped'),
        type: 'error',
      };

    case COMPLETED:
      return {
        text: i18n.t('workflow.state_success'),
        type: 'success',
      };

    case FAILED:
      return {
        text: i18n.t('workflow.state_failed'),
        type: 'error',
      };

    case INVALID:
      return {
        text: i18n.t('workflow.state_invalid'),
        type: 'default',
      };
    case UNKNOWN:
    default:
      return {
        text: i18n.t('workflow.state_unknown'),
        type: 'default',
      };
  }
}

// --------------- Misc ----------------
export function findJobExeInfoByJobDef(jobDef: Job, workflow: WorkflowExecutionDetails) {
  return workflow.jobs?.find((exeInfo) => {
    return (
      exeInfo.name === `${workflow.uuid}-${jobDef.name}` ||
      /* istanbul ignore next */
      exeInfo.name === `${workflow.name}-${jobDef.name}` ||
      /* istanbul ignore next */
      exeInfo.name.endsWith(jobDef.name)
    );
  });
}
