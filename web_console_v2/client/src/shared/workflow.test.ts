import {
  withExecutionDetail,
  pendingAcceptAndConfig,
  newlyCreated,
  completed,
} from 'services/mocks/v2/workflows/examples';
import {
  findJobExeInfoByJobDef,
  isAwaitParticipantConfig,
  isCompleted,
  isPendingAccpet,
} from './workflow';

describe('Workflow state judgement', () => {
  it('All should works fine', () => {
    expect(isAwaitParticipantConfig(newlyCreated)).toBeTruthy();
    expect(isCompleted(completed)).toBeTruthy();
    expect(isPendingAccpet(pendingAcceptAndConfig)).toBeTruthy();
  });
});

describe('Misc workflow helpers', () => {
  it('Find job execution details by', () => {
    expect(findJobExeInfoByJobDef({ name: 'Initiative' } as any, withExecutionDetail)).toBe(
      withExecutionDetail.jobs[0],
    );
  });
});
