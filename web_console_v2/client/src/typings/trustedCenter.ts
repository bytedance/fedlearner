export enum TrustedJobGroupDisplayStatus {
  CREATE_PENDING = 'CREATE_PENDING',
  CREATE_FAILED = 'CREATE_FAILED',
  TICKET_PENDING = 'TICKET_PENDING',
  TICKET_DECLINED = 'TICKET_DECLINED',
  SELF_AUTH_PENDING = 'SELF_AUTH_PENDING',
  PART_AUTH_PENDING = 'PART_AUTH_PENDING',
  JOB_PENDING = 'JOB_PENDING',
  JOB_RUNNING = 'JOB_RUNNING',
  JOB_SUCCEEDED = 'JOB_SUCCEEDED',
  JOB_FAILED = 'JOB_FAILED',
  JOB_STOPPED = 'JOB_STOPPED',
}

export enum TrustedJobGroupStatus {
  PENDING = 'PENDING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
}

export enum AuthStatus {
  PENDING = 'PENDING',
  WITHDRAW = 'WITHDRAW',
  AUTHORIZED = 'AUTHORIZED',
}

export enum TrustedJobType {
  ANALYZE = 'ANALYZE',
  EXPORT = 'EXPORT',
}

export enum TrustedJobStatus {
  NEW = 'NEW',
  CREATED = 'CREATED',
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  SUCCEEDED = 'SUCCEEDED',
  FAILED = 'FAILED',
  STOPPED = 'STOPPED',
}

export enum TicketStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  DECLINED = 'DECLINED',
}

export enum TrustedJobRole {
  COORDINATOR = 'COORDINATOR',
  PARTICIPANT = 'PARTICIPANT',
}

export enum ResourceTemplateType {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  CUSTOM = 'custom',
}

export enum NotificationType {
  TRUSTED_JOB_GROUP_CREATE = 'TRUSTED_JOB_GROUP_CREATE',
  TRUSTED_JOB_EXPORT = 'TRUSTED_JOB_EXPORT',
}

export enum TrustedJobParamType {
  ANALYZE = 'ANALYZE',
  EXPORT = 'EXPORT',
}

export enum TicketAuthStatus {
  CREATE_PENDING = 'CREATE_PENDING',
  CREATE_FAILED = 'CREATE_FAILED',
  TICKET_PENDING = 'TICKET_PENDING',
  TICKET_DECLINED = 'TICKET_DECLINED',
  AUTH_PENDING = 'AUTH_PENDING',
  AUTHORIZED = 'AUTHORIZED',
}

export interface TrustedJobResource {
  cpu: number;
  memory: number;
  replicas?: number;
}

export type ParticipantDataset = {
  participant_id: ID;
  uuid: ID;
  name: string;
};

export type TrustedJobGroupPayload = {
  name?: string;
  comment?: string;
  algorithm_id?: ID;
  dataset_id?: ID;
  participant_datasets?: ParticipantDataset[];
  resource?: TrustedJobResource;
  auth_status?: AuthStatus;
};

export type datasetConstruct = {
  items: ParticipantDataset[];
};

export type TrustedJobGroup = {
  id: ID;
  name: string;
  uuid: ID;
  latest_version: string;
  comment: string;
  project_id: ID;
  creator_username?: string;
  created_at?: DateTime;
  updated_at?: DateTime;
  analyzer_id?: ID;
  coordinator_id?: ID;
  ticket_uuid: ID;
  ticket_status: TicketStatus;
  status?: TrustedJobGroupStatus;
  auth_status?: AuthStatus;
  latest_job_status?: TrustedJobStatus;
  ticket_auth_status: TicketAuthStatus;
  unauth_participant_ids?: ID[];
  algorithm_id?: ID;
  algorithm_participant_id?: ID;
  algorithm_uuid?: string;
  algorithm_project_uuid?: string;
  resource?: TrustedJobResource;
  dataset_id?: ID;
  creator_name: string;
  participant_datasets: datasetConstruct;
};

export type TrustedJobGroupItem = {
  id: ID;
  name: string;
  created_at: DateTime;
  is_creator: boolean;
  creator_id: ID;
  ticket_status: TicketStatus;
  is_configured?: boolean;
  status?: TrustedJobGroupStatus;
  auth_status?: AuthStatus;
  latest_job_status?: TrustedJobStatus;
  ticket_auth_status?: TicketAuthStatus;
  participants_info: any;
  unauth_participant_ids?: ID[];
};

export type TrustedJob = {
  id: ID;
  name: string;
  coordinator_id?: ID;
  type?: TrustedJobType;
  job_id: ID;
  uuid: ID;
  version: number;
  comment: string;
  project_id: ID;
  trusted_job_group_id: ID;
  started_at: DateTime;
  finished_at: DateTime;
  status: TrustedJobStatus;
  algorithm_id: ID;
  algorithm_uuid: ID;
  resource: TrustedJobResource;
  auth_status: AuthStatus;
  dataset_job_id: ID;
  ticket_uuid?: ID;
  ticket_status?: string;
  ticket_auth_status: TicketAuthStatus;
  export_dataset_id?: ID;
};

export type TrustedJobListItem = {
  id: ID;
  name: string;
  type?: TrustedJobType;
  job_id: ID;
  comment: string;
  started_at: DateTime;
  finished_at: DateTime;
  status: TrustedJobStatus;
  ticket_auth_status: TicketAuthStatus;
  coordinator_id?: ID;
};

export type Instance = {
  id: ID;
  status: TrustedJobStatus;
  created_at: DateTime;
  resource: TrustedJobResource;
};

export type NotificationItem = {
  type: NotificationType;
  id: ID;
  name: string;
  created_at: DateTime;
  coordinator_id: ID;
};

export enum TrustedJobGroupTabType {
  COMPUTING = 'computing',
  EXPORT = 'export',
}
