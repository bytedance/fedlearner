import { AxiosRequestConfig } from 'axios';
import { pendingAcceptAndConfig, withExecutionDetail, completed } from '../examples';

const get = (config: AxiosRequestConfig) => {
  const rets: Record<ID, any> = {
    1: pendingAcceptAndConfig,
    2: withExecutionDetail,
    3: completed,
  };

  return {
    data: { data: rets[config._id!] },
    status: 200,
  };
};

export const put = {
  data: { data: { success: true } },
  status: 200,
};

export const patch = {
  data: { data: { success: true } },
  status: 200,
};

export default get;
