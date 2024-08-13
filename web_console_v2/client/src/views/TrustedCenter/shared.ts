import styled from 'styled-components';
import { MixinSquare } from 'styles/mixins';
import atomIcon from 'assets/icons/atom-icon-algorithm-management.svg';
import {
  AuthStatus,
  ResourceTemplateType,
  TicketAuthStatus,
  TicketStatus,
  TrustedJobGroup,
  TrustedJobResource,
} from 'typings/trustedCenter';

export const Avatar = styled.div<{ bgSrc?: string }>`
  ${MixinSquare(48)};
  background-color: var(--primary-1);
  color: white;
  border-radius: 4px;
  font-size: 18px;
  text-align: center;

  &::before {
    display: inline-block;
    width: 100%;
    height: 100%;
    content: '';
    background: url(${(props) => props.bgSrc || atomIcon}) no-repeat;
    background-size: contain;
  }
`;

export const AuthStatusMap: Record<AuthStatus, string> = {
  [AuthStatus.AUTHORIZED]: '已授权',
  [AuthStatus.PENDING]: '待授权',
  [AuthStatus.WITHDRAW]: '拒绝授权',
};

export function getResourceConfigInitialValues(resource: TrustedJobResource) {
  return {
    master_cpu: '0m',
    master_mem: '0Gi',
    master_replicas: '1',
    master_roles: 'master',
    ps_cpu: '0m',
    ps_mem: '0Gi',
    ps_replicas: '1',
    ps_roles: 'ps',
    resource_type: ResourceTemplateType.CUSTOM,
    worker_cpu: resource.cpu + 'm',
    worker_mem: resource.memory + 'Gi',
    worker_replicas: String(resource.replicas),
    worker_roles: 'worker',
  };
}

export const defaultTrustedJobGroup: TrustedJobGroup = {
  id: 0,
  name: '',
  uuid: 0,
  latest_version: '1',
  comment: '',
  project_id: 0,
  ticket_uuid: 0,
  ticket_status: TicketStatus.PENDING,
  ticket_auth_status: TicketAuthStatus.CREATE_PENDING,
  creator_name: '',
  participant_datasets: {
    items: [],
  },
  resource: {
    cpu: 4,
    memory: 8,
    replicas: 1,
  },
};
