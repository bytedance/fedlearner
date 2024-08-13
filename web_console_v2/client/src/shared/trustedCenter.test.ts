import {
  AuthStatus,
  TicketAuthStatus,
  TicketStatus,
  TrustedJobStatus,
} from 'typings/trustedCenter';
import {
  getLatestJobStatus,
  getTicketAuthStatus,
  getTrustedJobGroupAuthStatus,
  getTrustedJobStatus,
} from './trustedCenter';

describe('trusted center shared function', () => {
  const groupData: any = {
    id: 1,
    name: 'Trusted Computing',
    created_at: Date.now(),
    is_creator: true,
    creator_id: 323,
    auth_status: AuthStatus.AUTHORIZED,
    ticket_status: TicketStatus.PENDING,
    latest_job_status: undefined,
  };

  const jobData: any = {
    id: 1,
    name: 'Trusted Job',
    job_id: 12,
    comment: 'useful',
    started_at: Date.now(),
    finished_at: Date.now(),
    status: undefined,
  };

  const tempJobData: any = undefined;

  /** getTrustedJobStatus */

  it('get job no data status', () => {
    expect(getTrustedJobStatus(tempJobData)).toEqual({
      type: 'default',
      text: 'trusted_center.state_trusted_job_unknown',
      tip: '',
    });
  });

  it('get job data undefined status', () => {
    expect(getTrustedJobStatus(jobData)).toEqual({
      type: 'default',
      text: 'trusted_center.state_trusted_job_unknown',
      tip: '',
    });
  });

  it('get trusted job new status', () => {
    expect(getTrustedJobStatus({ ...jobData, status: TrustedJobStatus.NEW })).toEqual({
      type: 'default',
      text: '发起方创建成功',
      tip: '',
    });
  });

  it('get trusted job created status', () => {
    expect(getTrustedJobStatus({ ...jobData, status: TrustedJobStatus.CREATED })).toEqual({
      type: 'default',
      text: '多方创建成功',
      tip: '',
    });
  });

  it('get trusted job pending status', () => {
    expect(getTrustedJobStatus({ ...jobData, status: TrustedJobStatus.PENDING })).toEqual({
      type: 'default',
      text: 'trusted_center.state_trusted_job_pending',
      tip: '',
    });
  });

  it('get trusted job running status', () => {
    expect(getTrustedJobStatus({ ...jobData, status: TrustedJobStatus.RUNNING })).toEqual({
      type: 'processing',
      text: 'trusted_center.state_trusted_job_running',
      tip: '',
    });
  });

  it('get trusted job succeeded status', () => {
    expect(getTrustedJobStatus({ ...jobData, status: TrustedJobStatus.SUCCEEDED })).toEqual({
      type: 'success',
      text: 'trusted_center.state_trusted_job_succeeded',
      tip: '',
    });
  });

  it('get trusted job failed status', () => {
    expect(getTrustedJobStatus({ ...jobData, status: TrustedJobStatus.FAILED })).toEqual({
      type: 'error',
      text: 'trusted_center.state_trusted_job_failed',
      tip: '',
    });
  });

  it('get trusted job stopped status', () => {
    expect(getTrustedJobStatus({ ...jobData, status: TrustedJobStatus.STOPPED })).toEqual({
      type: 'error',
      text: 'trusted_center.state_trusted_job_stopped',
      tip: '',
    });
  });

  it('get trusted job undefined status', () => {
    expect(
      getTrustedJobGroupAuthStatus({
        ...groupData,
        auth_status: undefined,
      }),
    ).toEqual({
      type: 'default',
      text: 'trusted_center.state_trusted_job_unknown',
      tip: '',
    });
  });

  it('get trusted job authorization status', () => {
    expect(getTrustedJobGroupAuthStatus(groupData)).toEqual({
      type: 'success',
      text: 'trusted_center.state_auth_status_authorized',
      tip: '',
    });
  });

  it('get trusted job unauthorization status', () => {
    expect(
      getTrustedJobGroupAuthStatus({
        ...groupData,
        auth_status: AuthStatus.PENDING,
      }),
    ).toEqual({
      type: 'error',
      text: 'trusted_center.state_auth_status_unauthorized',
      tip: '',
    });
  });

  const exportJobData: any = {
    id: 1,
    name: 'Trusted Job',
    job_id: 12,
    comment: 'useful',
    started_at: Date.now(),
    finished_at: Date.now(),
    status: TrustedJobStatus.PENDING,
    ticket_auth_status: undefined,
  };

  const tempExportJobData: any = undefined;
  /** getTicketAuthStatus */

  it('get export job no data status', () => {
    expect(getTicketAuthStatus(tempExportJobData)).toEqual({
      type: 'normal',
      text: '未知',
      percent: 0,
      tip: '',
    });
  });

  it('get export job undefined status', () => {
    expect(getTicketAuthStatus(exportJobData)).toEqual({
      type: 'normal',
      text: '未知',
      percent: 0,
      tip: '',
    });
  });

  it('get export job create pending status', () => {
    expect(
      getTicketAuthStatus({
        ...exportJobData,
        ticket_auth_status: TicketAuthStatus.CREATE_PENDING,
      }),
    ).toEqual({
      type: 'normal',
      text: '创建中',
      percent: 10,
      tip: '',
    });
  });

  it('get export job create failed status', () => {
    expect(
      getTicketAuthStatus({
        ...exportJobData,
        ticket_auth_status: TicketAuthStatus.CREATE_FAILED,
      }),
    ).toEqual({
      type: 'error',
      text: '创建失败',
      percent: 100,
      tip: '',
    });
  });

  it('get export job ticket pending status', () => {
    expect(
      getTicketAuthStatus({
        ...exportJobData,
        ticket_auth_status: TicketAuthStatus.TICKET_PENDING,
      }),
    ).toEqual({
      type: 'normal',
      text: '待审批',
      percent: 20,
      tip: '',
    });
  });

  it('get export job ticket declined status', () => {
    expect(
      getTicketAuthStatus({
        ...exportJobData,
        ticket_auth_status: TicketAuthStatus.TICKET_DECLINED,
      }),
    ).toEqual({
      type: 'error',
      text: '审批失败',
      percent: 100,
      tip: '',
    });
  });

  it('get export job ticket auth pending status', () => {
    expect(
      getTicketAuthStatus({
        ...exportJobData,
        ticket_auth_status: TicketAuthStatus.AUTH_PENDING,
      }),
    ).toEqual({
      type: 'normal',
      text: '待授权',
      percent: 80,
      tip: '',
    });
  });

  it('get export job ticket authorized status', () => {
    expect(
      getTicketAuthStatus({
        ...exportJobData,
        ticket_auth_status: TicketAuthStatus.AUTHORIZED,
      }),
    ).toEqual({
      type: 'normal',
      text: '已授权',
      percent: 100,
      tip: '',
    });
  });

  /** getLatestJobStatus */
  it('get job no data status', () => {
    expect(getLatestJobStatus(tempJobData)).toEqual({
      type: 'default',
      text: '未知',
      tip: '',
    });
  });

  it('get job data undefined status', () => {
    expect(getLatestJobStatus(groupData)).toEqual({
      type: 'default',
      text: '未知',
      tip: '',
    });
  });

  it('get trusted job new status', () => {
    expect(getLatestJobStatus({ ...groupData, latest_job_status: TrustedJobStatus.NEW })).toEqual({
      type: 'success',
      text: '发起方创建成功',
      tip: '',
    });
  });

  it('get trusted job created status', () => {
    expect(
      getLatestJobStatus({ ...groupData, latest_job_status: TrustedJobStatus.CREATED }),
    ).toEqual({
      type: 'success',
      text: '多方创建成功',
      tip: '',
    });
  });

  it('get trusted job pending status', () => {
    expect(
      getLatestJobStatus({ ...groupData, latest_job_status: TrustedJobStatus.PENDING }),
    ).toEqual({
      type: 'default',
      text: '待执行',
      tip: '',
    });
  });

  it('get trusted job running status', () => {
    expect(
      getLatestJobStatus({ ...groupData, latest_job_status: TrustedJobStatus.RUNNING }),
    ).toEqual({
      type: 'processing',
      text: '执行中',
      tip: '',
    });
  });

  it('get trusted job succeeded status', () => {
    expect(
      getLatestJobStatus({ ...groupData, latest_job_status: TrustedJobStatus.SUCCEEDED }),
    ).toEqual({
      type: 'success',
      text: '已成功',
      tip: '',
    });
  });

  it('get trusted job failed status', () => {
    expect(
      getLatestJobStatus({ ...groupData, latest_job_status: TrustedJobStatus.FAILED }),
    ).toEqual({
      type: 'error',
      text: '已失败',
      tip: '',
    });
  });

  it('get trusted job stopped status', () => {
    expect(
      getLatestJobStatus({ ...groupData, latest_job_status: TrustedJobStatus.STOPPED }),
    ).toEqual({
      type: 'error',
      text: '已终止',
      tip: '',
    });
  });
});
