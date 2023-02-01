export enum ParticipantType {
  PLATFORM = 'PLATFORM',
  LIGHT_CLIENT = 'LIGHT_CLIENT',
}

export interface UpdateParticipantPayload {
  name?: string;
  domain_name?: string;
  grpc_ssl_server_host: string;
  host?: number;
  port?: string;
  certificates?: string;
  comment?: string;
  type: ParticipantType | `${ParticipantType}`;
}

export interface CreateParticipantPayload {
  name: string;
  domain_name: string;
  is_manual_configured: boolean;
  grpc_ssl_server_host?: string;
  host?: string;
  port?: number;
  certificates?: string;
  comment?: string;
  type: ParticipantType | `${ParticipantType}`;
}

export interface Participant {
  id: number;
  name: string;
  domain_name: string;
  pure_domain_name: string;
  extra: {
    is_manual_configured: boolean;
    grpc_ssl_server_host?: string;
  };
  host?: string;
  port?: number;
  certificates?: string;
  comment?: string | null;
  created_at?: number;
  updated_at?: number;
  num_project?: number;
  type: ParticipantType | `${ParticipantType}`;
  last_connected_at?: number;
  support_blockchain?: boolean;
}

export enum ConnectionStatusType {
  Success = 'success',
  Fail = 'error',
  Processing = 'processing',
}

export interface Version {
  pub_date?: string;
  revision?: string;
  branch_name?: string;
  version?: string;
}

export interface ConnectionStatus {
  success: ConnectionStatusType;
  message: string;
  application_version: Version;
}

export interface DomainName {
  domain_name: string;
}
