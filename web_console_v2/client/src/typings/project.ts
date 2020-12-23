export interface PaginationConfig {
  total: number
  page_size: number
  page: number
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
