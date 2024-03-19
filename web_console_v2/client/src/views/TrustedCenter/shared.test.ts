import { getResourceConfigInitialValues } from './shared';
import { ResourceTemplateType, TrustedJobResource } from 'typings/trustedCenter';

describe('getResourceConfigInitialValues', () => {
  it('normal', () => {
    const resource: TrustedJobResource = {
      cpu: 16,
      memory: 32,
      replicas: 100,
    };
    expect(getResourceConfigInitialValues(resource)).toEqual({
      master_cpu: '0m',
      master_mem: '0Gi',
      master_replicas: '1',
      master_roles: 'master',
      ps_cpu: '0m',
      ps_mem: '0Gi',
      ps_replicas: '1',
      ps_roles: 'ps',
      resource_type: ResourceTemplateType.CUSTOM,
      worker_cpu: '16m',
      worker_mem: '32Gi',
      worker_replicas: '100',
      worker_roles: 'worker',
    });
  });
});
