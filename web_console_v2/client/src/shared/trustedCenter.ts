import { ProgressType, StateTypes } from 'components/StateIndicator';
import i18n from 'i18n';
import {
  TrustedJobGroupItem,
  TrustedJobStatus,
  AuthStatus,
  TrustedJobListItem,
  TrustedJobGroup,
  TicketAuthStatus,
  TrustedJob,
} from 'typings/trustedCenter';

// ------- judge trusted job status ------
export function getTrustedJobStatus(
  data: TrustedJobListItem | TrustedJob,
): { type: StateTypes; text: string; tip?: string } {
  let type: StateTypes = 'default';
  let text = i18n.t('trusted_center.state_trusted_job_unknown');
  const tip = '';

  if (!data) {
    return {
      type,
      text,
      tip,
    };
  }

  switch (data.status) {
    case TrustedJobStatus.NEW:
      type = 'default';
      text = '发起方创建成功';
      break;
    case TrustedJobStatus.CREATED:
      type = 'default';
      text = '多方创建成功';
      break;
    case TrustedJobStatus.PENDING:
      type = 'default';
      text = i18n.t('trusted_center.state_trusted_job_pending');
      break;
    case TrustedJobStatus.RUNNING:
      type = 'processing';
      text = i18n.t('trusted_center.state_trusted_job_running');
      break;
    case TrustedJobStatus.SUCCEEDED:
      type = 'success';
      text = i18n.t('trusted_center.state_trusted_job_succeeded');
      break;
    case TrustedJobStatus.FAILED:
      type = 'error';
      text = i18n.t('trusted_center.state_trusted_job_failed');
      break;
    case TrustedJobStatus.STOPPED:
      type = 'error';
      text = i18n.t('trusted_center.state_trusted_job_stopped');
      break;
    default:
      break;
  }
  return {
    type,
    text,
    tip,
  };
}

// ------ judge trusted job authorization status ------
export function getTrustedJobGroupAuthStatus(
  data: TrustedJobGroupItem,
): { type: StateTypes; text: string; tip?: string } {
  let type: StateTypes = 'default';
  let text = i18n.t('trusted_center.state_trusted_job_unknown');
  const tip = '';
  switch (data.auth_status) {
    case AuthStatus.AUTHORIZED:
      type = 'success';
      text = i18n.t('trusted_center.state_auth_status_authorized');
      break;
    case AuthStatus.PENDING:
      type = 'error';
      text = i18n.t('trusted_center.state_auth_status_unauthorized');
      break;
    default:
      break;
  }

  return {
    type,
    text,
    tip,
  };
}

// ------ judge ticket auth authorization status ------
export function getTicketAuthStatus(
  data: TrustedJobListItem | TrustedJob | TrustedJobGroupItem | TrustedJobGroup,
): { type: ProgressType; text: string; tip?: string; percent: number } {
  let type: ProgressType = 'normal';
  let text = '未知';
  const tip = '';
  let percent = 0;

  if (!data) {
    return {
      type,
      text,
      tip,
      percent,
    };
  }

  switch (data.ticket_auth_status) {
    case TicketAuthStatus.CREATE_PENDING:
      type = 'normal';
      text = '创建中';
      percent = 10;
      break;
    case TicketAuthStatus.CREATE_FAILED:
      type = 'error';
      text = '创建失败';
      percent = 100;
      break;
    case TicketAuthStatus.TICKET_PENDING:
      type = 'normal';
      text = '待审批';
      percent = 20;
      break;
    case TicketAuthStatus.TICKET_DECLINED:
      type = 'error';
      text = '审批失败';
      percent = 100;
      break;
    case TicketAuthStatus.AUTH_PENDING:
      type = 'normal';
      text = '待授权';
      percent = 80;
      break;
    case TicketAuthStatus.AUTHORIZED:
      type = 'normal';
      text = '已授权';
      percent = 100;
      break;
    default:
      break;
  }
  return {
    type,
    text,
    tip,
    percent,
  };
}

// ------ judge latest job status ------
export function getLatestJobStatus(
  data: TrustedJobGroupItem | TrustedJobGroup,
): { type: StateTypes; text: string; tip?: string } {
  let type: StateTypes = 'default';
  let text = '未知';
  const tip = '';

  if (!data) {
    return {
      type,
      text,
      tip,
    };
  }

  switch (data.latest_job_status) {
    case TrustedJobStatus.NEW:
      type = 'success';
      text = '发起方创建成功';
      break;
    case TrustedJobStatus.CREATED:
      type = 'success';
      text = '多方创建成功';
      break;
    case TrustedJobStatus.PENDING:
      type = 'default';
      text = '待执行';
      break;
    case TrustedJobStatus.RUNNING:
      type = 'processing';
      text = '执行中';
      break;
    case TrustedJobStatus.SUCCEEDED:
      type = 'success';
      text = '已成功';
      break;
    case TrustedJobStatus.FAILED:
      type = 'error';
      text = '已失败';
      break;
    case TrustedJobStatus.STOPPED:
      type = 'error';
      text = '已终止';
      break;
    default:
      break;
  }
  return {
    type,
    text,
    tip,
  };
}
