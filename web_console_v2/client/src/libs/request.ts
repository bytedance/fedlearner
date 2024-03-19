import axios, { AxiosInstance, Method } from 'axios';
import {
  getRequestMockState,
  isThisRequestMockEnabled,
  setRequestMockState,
} from 'components/MockDevtools/utils';
import i18n from 'i18n';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { removeFalsy, transformKeysToSnakeCase, binarizeBoolean } from 'shared/object';
import store from 'store2';
import { ErrorCodes } from 'typings/app';
import PubSub from 'pubsub-js';
import qs from 'qs';
import { getJWTHeaders, saveBlob } from 'shared/helpers';

declare module 'axios' {
  interface AxiosRequestConfig {
    singleton?: symbol;
    removeFalsy?: boolean;
    snake_case?: boolean;
    _id?: ID;
    disableExtractResponseData?: boolean;
  }
  interface AxiosInstance {
    download(url: string, method?: Method, filename?: string): Promise<string | undefined>;
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

export const BASE_URL = '/api';

let request: AxiosInstance;

const errorCodeToErrorMessageMap: {
  [code: number]: string;
} = {
  [ErrorCodes.TokenExpired]: i18n.t('error.token_expired'),
  [ErrorCodes.Unauthorized]: i18n.t('error.unauthorized'),
};

if (process.env.NODE_ENV === 'development' || process.env.REACT_APP_ENABLE_FULLY_MOCK) {
  // NOTE: DEAD CODES HERE
  // will be removed during prod building

  request = axios.create({
    baseURL: BASE_URL,
    paramsSerializer: function (params) {
      return qs.stringify(params, {
        arrayFormat: 'repeat',
      });
    },
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

  request.interceptors.request.use((config) => {
    if (isThisRequestMockEnabled(config) || process.env.REACT_APP_ENABLE_FULLY_MOCK === 'true') {
      config.url = '/mock/20021' + config.url;
      config.baseURL = '';
    }
    return config;
  });
} else {
  request = axios.create({
    baseURL: BASE_URL,
    paramsSerializer: function (params) {
      return qs.stringify(params, {
        arrayFormat: 'repeat',
      });
    },
  });
}

/**
 * Authorization interceptor
 */
request.interceptors.request.use((config) => {
  config.headers = { ...config.headers, ...getJWTHeaders() };
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

/**
 * Extract data handler & Error prehandler
 */
request.interceptors.response.use(
  (response) => {
    if (response?.config?.disableExtractResponseData) {
      return response;
    }
    return response.data;
  },
  (error) => {
    return new Promise((resolve, reject) => {
      const response = error.response.data;

      // Access token expired due to time fly or server reboot
      if (response.code === ErrorCodes.TokenExpired || response.code === ErrorCodes.Unauthorized) {
        const errorMessage = response.message || errorCodeToErrorMessageMap[response.code];
        store.remove(LOCAL_STORAGE_KEYS.current_user);
        store.remove(LOCAL_STORAGE_KEYS.sso_info);
        // Trigger logout event
        PubSub.publish('logout', {
          message: errorMessage,
        });
        return reject(new ServerError(errorMessage, response.code));
      }

      if (
        error.response &&
        error.response.config.responseType === 'blob' &&
        response.type === 'application/json'
      ) {
        const { data, status, statusText } = error.response;

        // Parse response(Blob) as JSON
        const reader = new FileReader();
        reader.addEventListener('abort', reject);
        reader.addEventListener('error', reject);
        reader.addEventListener('loadend', () => {
          try {
            const resp = JSON.parse(reader.result as string);
            const { details } = resp;

            const serverError = new ServerError(
              typeof details === 'object'
                ? JSON.stringify(details)
                : details || resp.message || resp.msg || statusText,
              status,
              resp,
            );

            return reject(serverError);
          } catch (error) {
            return reject(error);
          }
        });
        reader.readAsText(data);
      } else {
        // Common errors handle
        if (response && typeof response === 'object') {
          const { data, status, statusText } = error.response;
          const { details } = data;

          const serverError = new ServerError(
            typeof details === 'object'
              ? JSON.stringify(details)
              : details || data.message || data.msg || statusText,
            status,
            data,
          );

          return reject(serverError);
        }

        return reject(error);
      }
    });
  },
);

const SingletonCollection = new Map();

/**
 * Singleton control interceptor
 */
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

request.download = async function (url, method = 'GET', filename = '') {
  const { headers, data, status } = await request(url, {
    method,
    responseType: 'blob',
    disableExtractResponseData: true,
  });
  if (status === 204) {
    return i18n.t('message_no_file');
  }

  const contentDisposition =
    headers?.['content-disposition'] ?? headers?.['Content-Disposition'] ?? '';
  const finalFilename = filename || (contentDisposition?.split('filename=')[1] ?? '');
  saveBlob(data, finalFilename);
};

export default request;
