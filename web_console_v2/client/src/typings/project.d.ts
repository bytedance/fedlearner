declare interface PaginationConfig {
  total: number
  page_size: number
  page: number
}

declare interface Variable {
  name: string
  value: string
}

declare interface Participant {
  name: string
  domain_name: string
  url: string
  certificates?: string | null
}

declare interface UpdateProjectFormData {
  token?: string
  variables?: Variable[]
  comment: string
}

declare interface CreateProjectFormData {
  name: string
  config: {
    token?: string
    participants: Participant[]
    variables: Variable[]
  }
  comment: string
}
declare interface Project extends CreateProjectFormData {
  id: number
  token: string
  created_at: number
  updated_at: number
  deleted_at: null
}

declare interface ProjectList {
  project_list: Project[]
  pagination: PaginationConfig
}

declare interface FormInitialValues {
  certificateConfigType: number
  name: string
  participantName: string
  participantUrl: string
  participantDomainName: string
  comment: string
  variables?: Variable[]
}
