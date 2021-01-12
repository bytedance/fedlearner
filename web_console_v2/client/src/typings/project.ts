import { PaginationConfig } from './component'

export enum ProjectConnectionStatus {
  Success,
  Waiting,
  Checking,
  Failed,
}

export enum CertificateConfigType {
  Upload,
  BackendConfig,
}
export interface Variable {
  name: string
  value: string
}

export interface Participant {
  name: string
  domain_name: string
  url: string
  certificates?: string | null
}

export interface UpdateProjectFormData {
  token?: string
  variables?: Variable[]
  comment: string
}

export interface CreateProjectFormData {
  name: string
  config: {
    token?: string
    participants: Participant[]
    variables: Variable[]
  }
  comment: string
}
export interface Project extends CreateProjectFormData {
  id: number
  token: string
  created_at: number
  updated_at: number
  deleted_at: null
}

export interface ProjectList {
  project_list: Project[]
  pagination: PaginationConfig
}

export interface ProjectFormInitialValues {
  certificateConfigType: number
  name: string
  participantName: string
  participantUrl: string
  participantDomainName: string
  comment: string
  variables?: Variable[]
}

export function getConnectionStatusClassName(status: ProjectConnectionStatus) {
  switch (status) {
    case ProjectConnectionStatus.Success:
      return 'success'
    case ProjectConnectionStatus.Waiting:
      return 'warning'
    case ProjectConnectionStatus.Checking:
      return 'primary'
    case ProjectConnectionStatus.Failed:
      return 'fail'
    default:
      return 'unknown' as never
  }
}
export function getConnectionStatusTag(status: ProjectConnectionStatus): string {
  switch (status) {
    case ProjectConnectionStatus.Success:
      return 'project.connection_status_success'
    case ProjectConnectionStatus.Waiting:
      return 'project.connection_status_waiting'
    case ProjectConnectionStatus.Checking:
      return 'project.connection_status_checking'
    case ProjectConnectionStatus.Failed:
      return 'project.connection_status_failed'
    default:
      return 'project.connection_status_waiting' as never
  }
}
