import { PaginationConfig } from './component';

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
    token: string;
    participants: Participant[];
    variables: ProjectVariable[];
  };
  comment: string;
}
export interface Project extends CreateProjectPayload {
  id: number;
  token: string;
  created_at: number;
  updated_at: number;
  deleted_at: null;
  num_workflow: number;
}

export interface ProjectList {
  project_list: Project[];
  pagination: PaginationConfig;
}

export interface ProjectFormInitialValues {
  certificateConfigType: number;
  name: string;
  participantName: string;
  participantUrl: string;
  participantDomainName: string;
  comment: string;
  variables?: ProjectVariable[];
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
      return 'project.connection_status_success';
    case ConnectionStatus.Waiting:
      return 'project.connection_status_waiting';
    case ConnectionStatus.Checking:
      return 'project.connection_status_checking';
    case ConnectionStatus.Failed:
      return 'project.connection_status_failed';
    case ConnectionStatus.CheckFailed:
      return 'project.connection_status_check_failed';
    default:
      return 'project.connection_status_waiting' as never;
  }
}
