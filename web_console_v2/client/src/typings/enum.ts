export enum FedLanguages {
  Chinese = 'cn',
  English = 'en',
}

export enum FedRoles {
  Admin,
  Operator,
}

export enum ConnectionStatus {
  Success,
  Waiting,
  Checking,
  Failed,
}

export enum CertificateConfigType {
  Upload,
  BackendConfig,
}

export enum DisplayType {
  Card = 1,
  Table = 2,
}

export function getConnectionStatusClassName(status: ConnectionStatus): string {
  switch (status) {
    case ConnectionStatus.Success:
      return 'success'
    case ConnectionStatus.Waiting:
      return 'waiting'
    case ConnectionStatus.Checking:
      return 'checking'
    case ConnectionStatus.Failed:
      return 'failed'
    default:
      return 'waiting' as never
  }
}
export function getConnectionStatusTag(status: ConnectionStatus): string {
  switch (status) {
    case ConnectionStatus.Success:
      return 'project.connection_status_success'
    case ConnectionStatus.Waiting:
      return 'project.connection_status_waiting'
    case ConnectionStatus.Checking:
      return 'project.connection_status_checking'
    case ConnectionStatus.Failed:
      return 'project.connection_status_failed'
    default:
      return 'project.connection_status_waiting' as never
  }
}
