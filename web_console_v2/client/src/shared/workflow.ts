import { Workflow, WorkflowState, TransactionState } from 'typings/workflow';
import i18n from 'i18n';
import { StateTypes } from 'components/StateIndicator';

const { NEW, READY: W_READY, RUNNING, STOPPED, INVALID, COMPLETED } = WorkflowState;
const {
  READY: T_READY,
  COORDINATOR_PREPARE,
  COORDINATOR_COMMITTABLE,
  COORDINATOR_COMMITTING,
  PARTICIPANT_PREPARE,
  PARTICIPANT_COMMITTABLE,
  PARTICIPANT_COMMITTING,
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
  const { state, target_state, transaction_state, config } = workflow;

  return (
    state === NEW &&
    target_state === W_READY &&
    transaction_state === PARTICIPANT_PREPARE &&
    config === null
  );
}

export function isWarmUpUnderTheHood(workflow: Workflow) {
  const { state, target_state, transaction_state } = workflow;
  return (
    state === NEW &&
    target_state === W_READY &&
    [
      PARTICIPANT_PREPARE,
      COORDINATOR_COMMITTING,
      PARTICIPANT_COMMITTABLE,
      PARTICIPANT_COMMITTING,
    ].includes(transaction_state)
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

  return target_state === RUNNING || (state === RUNNING && target_state === INVALID);
}

export function isPreparingStop(workflow: Workflow) {
  const { state, target_state } = workflow;

  return target_state === STOPPED && state === RUNNING;
}

export function isStopped(workflow: Workflow) {
  const { state, target_state } = workflow;

  return target_state === STOPPED || (state === STOPPED && target_state === INVALID);
}

export function isCompleted(workflow: Workflow) {
  const { state } = workflow;

  return state === COMPLETED;
}

// --------------- Xable judgement ----------------

/**
 * When target_state is not INVALID,
 * means underlying service of two sides are communicating
 * during which user can not perform any action to this workflow
 * server would response 'bad request'
 */
export function isOperable(workflow: Workflow) {
  return workflow.target_state === INVALID;
}

export function isForkable(workflow: Workflow) {
  const { state } = workflow;
  return [RUNNING, STOPPED, W_READY].includes(state);
}

// --------------- General stage getter ----------------

export function getWorkflowStage(workflow: Workflow): { type: StateTypes; text: string } {
  if (isAwaitParticipantConfig(workflow)) {
    return {
      text: i18n.t('workflow.state_configuring'),
      type: 'processing',
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
      type: 'processing',
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

  return {
    text: i18n.t('workflow.state_unknown'),
    type: 'default',
  };
}
