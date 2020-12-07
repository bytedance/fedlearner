declare interface Project {
  name: string
  time: number
}

declare interface ProjectList {
  project_list: Project[]
  pagination: PaginationConfig
}

declare interface PaginationConfig {
  total: number
  page_size: number
  page: number
}
