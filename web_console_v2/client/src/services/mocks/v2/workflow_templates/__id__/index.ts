import { AxiosRequestConfig } from 'axios';
import {
  normalTemplate,
  complexDepsTemplate,
  xShapeTemplate,
  localTpl,
  withTypedValueTemplate,
  noTypedValueTemplate,
} from '../examples';

const get = (config: AxiosRequestConfig) => {
  const rets: Record<ID, any> = {
    1: normalTemplate,
    2: complexDepsTemplate,
    3: xShapeTemplate,
    4: localTpl,
    5: withTypedValueTemplate,
    6: noTypedValueTemplate,
  };

  return {
    data: { data: rets[config._id!] },
    status: 200,
  };
};

export default get;
