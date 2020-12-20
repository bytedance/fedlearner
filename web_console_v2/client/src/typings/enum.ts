export enum FedLanguages {
  Chinese = 'cn',
  English = 'en',
}

export enum FedRoles {
  Admin,
  Operator,
}

export enum ConnectStatus {
  Success,
  Waiting,
  Checking,
  Failed,
}

export function getConnectStatusClassName(status: ConnectStatus): string {
  switch (status) {
    case ConnectStatus.Success:
      return 'success'
    case ConnectStatus.Waiting:
      return 'waiting'
    case ConnectStatus.Checking:
      return 'checking'
    case ConnectStatus.Failed:
      return 'failed'
    default:
      return 'waiting' as never
  }
}
export function getConnectStatusTag(status: ConnectStatus): string {
  switch (status) {
    case ConnectStatus.Success:
      return 'project_connect_status_success'
    case ConnectStatus.Waiting:
      return 'project_connect_status_waiting'
    case ConnectStatus.Checking:
      return 'project_connect_status_checking'
    case ConnectStatus.Failed:
      return 'project_connect_status_failed'
    default:
      return 'project_connect_status_waiting' as never
  }
}
