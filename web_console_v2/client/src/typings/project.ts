import { PaginationConfig } from './component';
import { Participant as NewParticipant, ParticipantType } from 'typings/participant';

export enum ConnectionStatus {
  Success,
  Waiting,
  Checking,
  Failed,
  CheckFailed,
}

export enum CertificateConfigType {
  Upload,
  BackendConfig,
}
export interface ProjectVariable {
  name: string;
  value: string;
}

export interface Participant {
  name: string;
  domain_name: string;
  pure_domain_name?: string;
  url: string;
  certificates?: string | null;
}

export interface UpdateProjectPayload {
  token?: string;
  variables?: ProjectVariable[];
  participant_name: string;
  comment: string;
}

export interface CreateProjectPayload {
  name: string;
  config: {
    participants: Participant[];
    variables: ProjectVariable[];
    abilities?: ProjectTaskType[];
    action_rules?: Record<ProjectActionType, ProjectAbilityType>;
    support_blockchain?: boolean;
  };
  comment: string;
}

export interface CreatePendingProjectPayload {
  name: string;
  config: {
    participants?: Participant[];
    variables?: ProjectVariable[];
    abilities?: ProjectTaskType[];
    action_rules?: Record<ProjectActionType, ProjectAbilityType>;
    support_blockchain?: boolean;
  };
  participant_id: ID[];
}

export interface FetchPendingProjectsPayload {
  filter?: string;
  page?: number;
  page_size?: number;
}

export interface AbilityAuth {}
export interface Project extends CreateProjectPayload {
  id: ID;
  uuid?: ID;
  token: string;
  created_at: number;
  updated_at: number;
  deleted_at: null;
  num_workflow: number;
  participants: NewParticipant[];
  variables: ProjectVariable[];
  creator: string;
  creator_username?: string;
  role: RoleType;
  participant_type?: ParticipantType;
  project_task_type: ProjectTaskType;
  participants_info: { ['participants_map']: Record<string, ParticiPantMap> };
  state: ProjectStateType;
  ticket_status: ProjectTicketStatus;
}
//export interface Complete
export interface ParticiPantMap {
  name: string;
  domain_name: string;
  role: RoleType;
}

export enum RoleType {
  COORDINATOR = 'COORDINATOR',
  PARTICIPANT = 'PARTICIPANT',
}

export interface ProjectList {
  project_list: Project[];
  pagination: PaginationConfig;
}

export interface ProjectFormInitialValues {
  certificateConfigType?: number;
  name: string;
  participantName?: string;
  participantUrl?: string;
  participantDomainName?: string;
  comment: string;
  variables?: ProjectVariable[];
  participants?: NewParticipant[];
  config?: ProjectConfig;
}
export interface ProjectConfig {
  participants?: Participant[];
  variables?: ProjectVariable[];
  abilities?: ProjectTaskType[];
  action_rules?: Record<ProjectActionType, ProjectAbilityType>;
  support_blockchain?: boolean;
}

export function getConnectionStatusClassName(status: ConnectionStatus) {
  switch (status) {
    case ConnectionStatus.Success:
      return 'success';
    case ConnectionStatus.Waiting:
      return 'warning';
    case ConnectionStatus.Checking:
      return 'processing';
    case ConnectionStatus.Failed:
      return 'error';
    case ConnectionStatus.CheckFailed:
      return 'error';
    default:
      return 'default' as never;
  }
}
export function getConnectionStatusTag(status: ConnectionStatus): string {
  switch (status) {
    case ConnectionStatus.Success:
      return '成功';
    case ConnectionStatus.Waiting:
      return '待检查';
    case ConnectionStatus.Checking:
      return '检查中';
    case ConnectionStatus.Failed:
      return '失败';
    case ConnectionStatus.CheckFailed:
      return '请重新检查';
    default:
      return '待检查' as never;
  }
}

export interface NewCreateProjectPayload {
  name: string;
  config: {
    variables: ProjectVariable[];
    abilities?: ProjectTaskType[];
    action_rules?: Record<string, string>;
    support_blockchain?: boolean;
  };
  participant_ids: ID[];
  comment: string;
}

export enum ProjectListType {
  COMPLETE = 'complete',
  PENDING = 'pending',
}

export enum ProjectTaskType {
  ALIGN = 'ID_ALIGNMENT',
  HORIZONTAL = 'HORIZONTAL_FL',
  VERTICAL = 'VERTICAL_FL',
  TRUSTED = 'TEE',
}

export enum ProjectAbilityType {
  ALWAYS_ALLOW = 'ALWAYS_ALLOW',
  ONCE = 'ONCE',
  MANUAL = 'MANUAL',
  ALWAYS_REFUSE = 'ALWAYS_REFUSE',
}

export enum ProjectActionType {
  ID_ALIGNMENT = 'ID_ALIGNMENT',
  DATA_ALIGNMENT = 'DATA_ALIGNMENT',
  HORIZONTAL_TRAIN = 'HORIZONTAL_TRAIN',
  VERTICAL_TRAIN = 'VERTICAL_TRAIN',
  VERTICAL_EVAL = 'VERTICAL_EVAL',
  VERTICAL_PRED = 'VERTICAL_PRED',
  VERTICAL_SERVING = 'VERTICAL_SERVING',
  WORKFLOW = 'WORKFLOW',
  TEE_SERVICE = 'TEE_SERVICE',
  TEE_RESULT_EXPORT = 'TEE_RESULT_EXPORT',
}

export enum ProjectStateType {
  PENDING = 'PENDING',
  ACCEPTED = 'ACCEPTED',
  FAILED = 'FAILED',
  CLOSED = 'CLOSED',
}

export enum ProjectTicketStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  DECLINED = 'DECLINED',
  FAILED = 'FAILED',
}

export enum ProjectBlockChainType {
  OPEN = '已开启',
  CLOSED = '未开启',
}

export enum ProjectBaseAbilitiesType {
  BASE = 'BASE',
}
