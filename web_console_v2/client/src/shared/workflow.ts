import {
  Workflow,
  WorkflowState,
  TransactionState,
  WorkflowExecutionDetails,
} from 'typings/workflow';
import i18n from 'i18n';
import { StateTypes } from 'components/StateIndicator';
import { Job } from 'typings/job';

const { NEW, READY: W_READY, RUNNING, STOPPED, INVALID, COMPLETED, FAILED } = WorkflowState;
const {
  READY: T_READY,
  COORDINATOR_PREPARE,
  COORDINATOR_COMMITTABLE,
  PARTICIPANT_PREPARE,
  PARTICIPANT_COMMITTABLE,
} = TransactionState;

// --------------- State judgement ----------------

export function isAwaitParticipantConfig(workflow: Workflow) {
  const { state, target_state, transaction_state } = workflow;

  return (
    state === NEW &&
    target_state === W_READY &&
    [T_READY, COORDINATOR_COMMITTABLE, COORDINATOR_PREPARE].includes(transaction_state)
  );
}

export function isPendingAccpet(workflow: Workflow) {
  const { state, target_state, transaction_state } = workflow;

  return state === NEW && target_state === W_READY && transaction_state === PARTICIPANT_PREPARE;
}

export function isWarmUpUnderTheHood(workflow: Workflow) {
  const { state, target_state, transaction_state } = workflow;
  return (
    state === NEW &&
    target_state === W_READY &&
    [PARTICIPANT_COMMITTABLE].includes(transaction_state)
  );
}

export function isReadyToRun(workflow: Workflow) {
  const { state, target_state, transaction_state } = workflow;

  return state === W_READY && target_state === INVALID && transaction_state === T_READY;
}

export function isPreparingRun(workflow: Workflow) {
  const { state, target_state } = workflow;

  return target_state === RUNNING && [W_READY, STOPPED].includes(state);
}

export function isRunning(workflow: Workflow) {
  const { state, target_state } = workflow;

  return state === RUNNING && target_state === INVALID;
}

export function isPreparingStop(workflow: Workflow) {
  const { state, target_state } = workflow;

  return target_state === STOPPED && [RUNNING, COMPLETED, FAILED].includes(state);
}

export function isStopped(workflow: Workflow) {
  const { state, target_state } = workflow;

  return target_state === STOPPED || (state === STOPPED && target_state === INVALID);
}

export function isCompleted(workflow: Workflow) {
  const { state } = workflow;

  return state === COMPLETED;
}

export function isFailed(workflow: Workflow) {
  const { state } = workflow;
  return state === FAILED;
}

export function isInvalid(workflow: Workflow) {
  const { state } = workflow;
  return state === INVALID;
}

// --------------- Xable judgement ----------------

/**
 * When target_state is not INVALID,
 * means underlying service of both sides are communicating
 * during which user cannot perform any action to this workflow
 * server would response 'bad request'
 */
export function isOperable(workflow: Workflow) {
  return workflow.target_state === INVALID;
}

export function isForkable(workflow: Workflow) {
  const { forkable } = workflow;
  return forkable;
}

// --------------- General stage getter ----------------

export function getWorkflowStage(workflow: Workflow): { type: StateTypes; text: string } {
  if (isAwaitParticipantConfig(workflow)) {
    return {
      text: i18n.t('workflow.state_configuring'),
      type: 'gold',
    };
  }

  if (isPendingAccpet(workflow)) {
    return {
      text: i18n.t('workflow.state_pending_accept'),
      type: 'warning',
    };
  }

  if (isWarmUpUnderTheHood(workflow)) {
    return {
      text: i18n.t('workflow.state_warmup_underhood'),
      type: 'warning',
    };
  }

  if (isPreparingRun(workflow)) {
    return {
      text: i18n.t('workflow.state_prepare_run'),
      type: 'warning',
    };
  }

  if (isReadyToRun(workflow)) {
    return {
      text: i18n.t('workflow.state_ready_to_run'),
      type: 'lime',
    };
  }

  if (isRunning(workflow)) {
    return {
      text: i18n.t('workflow.state_running'),
      type: 'processing',
    };
  }

  if (isPreparingStop(workflow)) {
    return {
      text: i18n.t('workflow.state_prepare_stop'),
      type: 'error',
    };
  }

  if (isStopped(workflow)) {
    return {
      text: i18n.t('workflow.state_stopped'),
      type: 'error',
    };
  }

  if (isCompleted(workflow)) {
    return {
      text: i18n.t('workflow.state_success'),
      type: 'success',
    };
  }

  if (isFailed(workflow)) {
    return {
      text: i18n.t('workflow.state_failed'),
      type: 'error',
    };
  }

  if (isInvalid(workflow)) {
    return {
      text: i18n.t('workflow.state_invalid'),
      type: 'default',
    };
  }

  return {
    text: i18n.t('workflow.state_unknown'),
    type: 'default',
  };
}

// --------------- Misc ----------------
export function findJobExeInfoByJobDef(jobDef: Job, workflow: WorkflowExecutionDetails) {
  return workflow.jobs.find((exeInfo) => {
    return (
      exeInfo.name === `${workflow.uuid}-${jobDef.name}` ||
      exeInfo.name === `${workflow.name}-${jobDef.name}` ||
      exeInfo.name.endsWith(jobDef.name)
    );
  });
}
