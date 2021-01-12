import axios, { AxiosInstance } from 'axios';
import { getRequestMockState, setRequestMockState } from 'components/_base/MockDevtools/utils';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { removeFalsy } from 'shared/object';
import store from 'store2';

declare module 'axios' {
  interface AxiosRequestConfig {
    singleton?: symbol;
    removeFalsy?: boolean;
  }
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

  request = axios.create({ adapter: require('./mockAdapter').default, baseURL: HOSTNAME });

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

/** Remove falsy value of params  */
request.interceptors.request.use((config) => {
  if (config.removeFalsy && config.params) {
    config.params = removeFalsy(config.params);
  }
  return config;
});

/** Error pre-handler */
request.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    const response = error.response.data;
    if (response && typeof response === 'object') {
      const serverError = new ServerError(error.response.data.message, error.satus);

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
