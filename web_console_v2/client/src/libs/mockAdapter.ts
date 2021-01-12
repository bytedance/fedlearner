import axios, { AxiosRequestConfig } from 'axios';
import { isThisRequestMockEnabled } from 'components/_base/MockDevtools/utils';
import { sleep } from 'shared/helpers';

async function axiosMockAdapter(config: AxiosRequestConfig) {
  if (isThisRequestMockEnabled(config) || process.env.REACT_APP_ENABLE_FULLY_MOCK === 'true') {
    try {
      await sleep(Math.random() * 1000);

      const method = config.method?.toLowerCase()!;

      let exportKey = 'default';

      if (method !== 'get') {
        exportKey = method;
      }

      const data = require(`../services/mocks${config.url}`)[exportKey];
      if (data.status === undefined) {
        console.error(
          `[⚠️ Mock Adapter]: the data /mocks/${config.url}.ts exported should have a status! e.g. 200`,
        );

        data.status = 200;
      }

      // HTTP code other than 2xx, 3xx should be rejected
      if (['2', '3'].includes(data.status.toString().charAt(0))) {
        return data;
      }
      return Promise.reject(data.data);
    } catch (error) {
      console.error('[⚠️ Mock Adapter]: ', error);
    }
  }

  return axios.defaults.adapter!(config);
}

export default axiosMockAdapter;
