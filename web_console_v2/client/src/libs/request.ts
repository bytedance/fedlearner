import axios, { AxiosInstance } from 'axios';
import { getRequestMockState, setRequestMockState } from 'components/_base/MockDevtools/utils';
import i18n from 'i18n';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { removeFalsy, transformKeysToSnakeCase, binarizeBoolean } from 'shared/object';
import store from 'store2';
import { ErrorCodes } from 'typings/app';

declare module 'axios' {
  interface AxiosRequestConfig {
    singleton?: symbol;
    removeFalsy?: boolean;
    snake_case?: boolean;
    _id?: ID;
  }

  // AxiosResponse has a struct like { data: YourRealResponse, status, config },
  // but we only want YourRealResponse as return,
  // thus we implement an interceptor to extract AxiosResponse.data
  // plus a typing overriding below to achieve the goal
  export interface AxiosResponse<T = any> extends Promise<T> {}
}

export class ServerError extends Error {
  code: number;
  extra: any;

  constructor(message: string, code: number, extra?: any) {
    super(message);
    this.name = 'ServerError';
    this.code = code;
    this.extra = extra;
  }
}

export const HOSTNAME = '/api';

let request: AxiosInstance;

if (process.env.NODE_ENV === 'development' || process.env.REACT_APP_ENABLE_FULLY_MOCK) {
  // NOTE: DEAD CODES HERE
  // will be removed during prod building

  request = axios.create({
    adapter: require('./mockAdapter').default,
    baseURL: HOSTNAME,
  });

  // Mock controlling
  request.interceptors.request.use((config) => {
    const key = `${config.method}|${config.url}`;
    const hasSet = typeof getRequestMockState(key) === 'boolean';

    if (!hasSet) {
      try {
        setRequestMockState(key, Boolean(process.env.REACT_APP_ENABLE_FULLY_MOCK));
      } catch {
        /** ignore error */
      }
    }

    return config;
  });
} else {
  request = axios.create({
    baseURL: HOSTNAME,
  });
}

/** Authorization interceptor */
request.interceptors.request.use((config) => {
  const token = store.get(LOCAL_STORAGE_KEYS.current_user)?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Params preprocessing (NOTE: every processor is optional):
 * 1. Remove undefined, null, empty string keys
 * 2. Turn camelCase keys to snake_case
 * 3. Turn true/false to 1/0
 */
request.interceptors.request.use((config) => {
  if (config.removeFalsy && config.params) {
    config.params = removeFalsy(config.params);
  }
  if (config.snake_case && config.params) {
    config.params = transformKeysToSnakeCase(config.params);
  }
  if (config.params) {
    config.params = binarizeBoolean(config.params);
  }
  return config;
});

/** Extract data handler & Error prehandler */
request.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const response = error.response.data;

    // Access token expired due to time fly or server reboot
    if (response.code === ErrorCodes.TokenExpired) {
      return Promise.reject(
        new ServerError(i18n.t('error.token_expired'), ErrorCodes.TokenExpired),
      );
    }
    // Common errors handle
    if (response && typeof response === 'object') {
      const serverError = new ServerError(
        error.response.data.details || error.response.data.message || error.response.data.msg,
        error.satus,
      );

      return Promise.reject(serverError);
    }

    return Promise.reject(error);
  },
);

const SingletonCollection = new Map();

/** Singleton control interceptor */
request.interceptors.request.use((config) => {
  if (config.singleton) {
    const oldSource = SingletonCollection.get(config.singleton);
    if (oldSource) {
      oldSource.cancel();
    }
    const source = axios.CancelToken.source();
    config.cancelToken = source.token;
    SingletonCollection.set(config.singleton, source);
  }

  return config;
});

request.interceptors.response.use(
  (response) => {
    if (response.config?.singleton) {
      SingletonCollection.delete(response.config.singleton);
    }
    return response;
  },
  (error) => {
    if (error?.config?.singleton) {
      SingletonCollection.delete(error.config.singleton);
    }
    return Promise.reject(error);
  },
);

export default request;
