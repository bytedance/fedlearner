import { Workflow, WorkflowState, TransactionState } from 'typings/workflow';
import i18n from 'i18n';
import { StateTypes } from 'components/StateIndicator';

const { NEW, READY: W_READY, RUNNING, STOPPED, INVALID, COMPLETED } = WorkflowState;
const {
  READY: T_READY,
  COORDINATOR_PREPARE,
  COORDINATOR_COMMITTABLE,
  PARTICIPANT_PREPARE,
} = TransactionState;

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

export function isReadyToRun(workflow: Workflow) {
  const { state, target_state, transaction_state } = workflow;

  return state === W_READY && target_state === INVALID && transaction_state === T_READY;
}

export function isRunning(workflow: Workflow) {
  const { state, target_state } = workflow;

  return target_state === RUNNING || (state === RUNNING && target_state === INVALID);
}

export function isStopped(workflow: Workflow) {
  const { state, target_state } = workflow;

  return target_state === STOPPED || (state === STOPPED && target_state === INVALID);
}

export function isCompleted(workflow: Workflow) {
  const { state } = workflow;

  return state === COMPLETED;
}

/**
 * When target_state is not INVALID,
 * means underlying service of two sides are communicating
 * during which user can not perform any action to this workflow
 * server would response 'bad request'
 */
export function isOperable(workflow: Workflow) {
  return workflow.target_state !== INVALID;
}

export function getWorkflowStage(workflow: Workflow): { type: StateTypes; text: string } {
  if (isAwaitParticipantConfig(workflow)) {
    return {
      text: i18n.t('workflow.state_configuring'),
      type: 'primary',
    };
  }

  if (isPendingAccpet(workflow)) {
    return {
      text: i18n.t('workflow.state_pending_accept'),
      type: 'warning',
    };
  }

  if (isReadyToRun(workflow)) {
    return {
      text: i18n.t('workflow.state_ready_to_run'),
      type: 'primary',
    };
  }

  if (isRunning(workflow)) {
    return {
      text: i18n.t('workflow.state_running'),
      type: 'primary',
    };
  }

  if (isStopped(workflow)) {
    return {
      text: i18n.t('workflow.state_stopped'),
      type: 'fail',
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
    type: 'unknown',
  };
}
