/* istanbul ignore file */

import { AxiosRequestConfig } from 'axios';
import { omit } from 'lodash-es';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import store from 'store2';

export function getMockConfigs() {
  return store.get(LOCAL_STORAGE_KEYS.mock_configs) || {};
}

export function isThisRequestMockEnabled(config: AxiosRequestConfig): boolean {
  const key = `${config.method}|${config.url}`;

  return Boolean(getRequestMockState(key));
}

export function getRequestMockState(key: string): boolean | undefined {
  return getMockConfigs()[key];
}

export function setRequestMockState(key: string, val: boolean): void {
  if (
    !['post', 'get', 'patch', 'delete', 'put', 'head', 'options', 'connect'].some((method) =>
      key.toLowerCase().startsWith(method),
    )
  ) {
    throw new Error('Key 名不合法！');
  }

  const mocksConfig = store.get(LOCAL_STORAGE_KEYS.mock_configs) || {};
  mocksConfig[key] = val;

  store.set(LOCAL_STORAGE_KEYS.mock_configs, mocksConfig);
}

export function removeRequestMock(key: string): void {
  const mocksConfig = getMockConfigs();

  store.set(LOCAL_STORAGE_KEYS.mock_configs, omit(mocksConfig, key));
}

export function toggleRequestMockState(key: string, val?: boolean): void {
  setRequestMockState(key, typeof val === 'boolean' ? val : !getRequestMockState(key));
}
