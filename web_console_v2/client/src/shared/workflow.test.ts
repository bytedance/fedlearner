import {
  withExecutionDetail,
  pendingAcceptAndConfig,
  newlyCreated,
  completed,
} from 'services/mocks/v2/workflows/examples';
import {
  findJobExeInfoByJobDef,
  getWorkflowStage,
  isOperable,
  isForkable,
  isEditable,
} from './workflow';
import { WorkflowState } from 'typings/workflow';

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

describe('Workflow state judgement', () => {
  it('All should works fine', () => {
    expect(getWorkflowStage(pendingAcceptAndConfig)).toEqual({
      text: 'workflow.state_pending_accept',
      type: 'warning',
    });
    expect(getWorkflowStage(newlyCreated)).toEqual({
      text: 'workflow.state_configuring',
      type: 'gold',
    });
    expect(getWorkflowStage(completed)).toEqual({
      text: 'workflow.state_success',
      type: 'success',
    });

    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: READY_TO_RUN })).toEqual({
      text: 'workflow.state_ready_to_run',
      type: 'lime',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: RUNNING })).toEqual({
      text: 'workflow.state_running',
      type: 'processing',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: STOPPED })).toEqual({
      text: 'workflow.state_stopped',
      type: 'error',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: COMPLETED })).toEqual({
      text: 'workflow.state_success',
      type: 'success',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: FAILED })).toEqual({
      text: 'workflow.state_failed',
      type: 'error',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: INVALID })).toEqual({
      text: 'workflow.state_invalid',
      type: 'default',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: PREPARE_RUN })).toEqual({
      text: 'workflow.state_prepare_run',
      type: 'warning',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: PREPARE_STOP })).toEqual({
      text: 'workflow.state_prepare_stop',
      type: 'error',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: WARMUP_UNDERHOOD })).toEqual({
      text: 'workflow.state_warmup_underhood',
      type: 'warning',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: PENDING_ACCEPT })).toEqual({
      text: 'workflow.state_pending_accept',
      type: 'warning',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: PARTICIPANT_CONFIGURING })).toEqual(
      {
        text: 'workflow.state_configuring',
        type: 'gold',
      },
    );
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: UNKNOWN })).toEqual({
      text: 'workflow.state_unknown',
      type: 'default',
    });
    expect(getWorkflowStage({ ...pendingAcceptAndConfig, state: UNKNOWN })).toEqual({
      text: 'workflow.state_unknown',
      type: 'default',
    });
  });

  it('IsOperable', () => {
    expect(isOperable(pendingAcceptAndConfig)).toBe(false);
    expect(isOperable(newlyCreated)).toBe(false);
    expect(isOperable(completed)).toBe(true);
    expect(isOperable({ ...pendingAcceptAndConfig, state: READY_TO_RUN })).toBe(true);
    expect(isOperable({ ...pendingAcceptAndConfig, state: RUNNING })).toBe(true);
    expect(isOperable({ ...pendingAcceptAndConfig, state: STOPPED })).toBe(true);
    expect(isOperable({ ...pendingAcceptAndConfig, state: COMPLETED })).toBe(true);
    expect(isOperable({ ...pendingAcceptAndConfig, state: FAILED })).toBe(true);
    expect(isOperable({ ...pendingAcceptAndConfig, state: INVALID })).toBe(false);
    expect(isOperable({ ...pendingAcceptAndConfig, state: PREPARE_RUN })).toBe(false);
    expect(isOperable({ ...pendingAcceptAndConfig, state: PREPARE_STOP })).toBe(false);
    expect(isOperable({ ...pendingAcceptAndConfig, state: WARMUP_UNDERHOOD })).toBe(false);
    expect(isOperable({ ...pendingAcceptAndConfig, state: PENDING_ACCEPT })).toBe(false);
    expect(isOperable({ ...pendingAcceptAndConfig, state: PARTICIPANT_CONFIGURING })).toBe(false);
    expect(isOperable({ ...pendingAcceptAndConfig, state: UNKNOWN })).toBe(false);
  });

  it('IsForkable', () => {
    expect(isForkable(pendingAcceptAndConfig)).toBe(true);
    expect(isForkable(newlyCreated)).toBe(true);
    expect(isForkable(completed)).toBe(true);
    expect(isForkable({ ...completed, forkable: true })).toBe(true);
    expect(isForkable({ ...completed, forkable: false })).toBe(false);
  });

  it('IsEditable', () => {
    expect(isEditable(pendingAcceptAndConfig)).toBe(false);
    expect(isEditable(newlyCreated)).toBe(true);
    expect(isEditable(completed)).toBe(true);
    expect(isEditable({ ...pendingAcceptAndConfig, state: READY_TO_RUN })).toBe(true);
    expect(isEditable({ ...pendingAcceptAndConfig, state: RUNNING })).toBe(false);
    expect(isEditable({ ...pendingAcceptAndConfig, state: STOPPED })).toBe(true);
    expect(isEditable({ ...pendingAcceptAndConfig, state: COMPLETED })).toBe(true);
    expect(isEditable({ ...pendingAcceptAndConfig, state: FAILED })).toBe(true);
    expect(isEditable({ ...pendingAcceptAndConfig, state: INVALID })).toBe(false);
    expect(isEditable({ ...pendingAcceptAndConfig, state: PREPARE_RUN })).toBe(false);
    expect(isEditable({ ...pendingAcceptAndConfig, state: PREPARE_STOP })).toBe(false);
    expect(isEditable({ ...pendingAcceptAndConfig, state: WARMUP_UNDERHOOD })).toBe(false);
    expect(isEditable({ ...pendingAcceptAndConfig, state: PENDING_ACCEPT })).toBe(false);
    expect(isEditable({ ...pendingAcceptAndConfig, state: PARTICIPANT_CONFIGURING })).toBe(true);
    expect(isEditable({ ...pendingAcceptAndConfig, state: UNKNOWN })).toBe(false);
  });
});

describe('Misc workflow helpers', () => {
  it('Find job execution details by', () => {
    expect(findJobExeInfoByJobDef({ name: 'Initiative' } as any, withExecutionDetail)).toBe(
      withExecutionDetail.jobs[0],
    );
  });
});
