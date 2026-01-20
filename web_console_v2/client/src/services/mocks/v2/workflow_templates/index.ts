import { stringifyComplexDictField } from 'shared/formSchema';
import { normalTemplate, localTpl } from './examples';

const normalTpl = stringifyComplexDictField(normalTemplate as any);

const get = {
  data: {
    data: [normalTpl, localTpl],
  },
  status: 200,
};

export const post = (config: any) => {
  return { data: { data: JSON.parse(config.data) }, status: 200 };
};

export default get;
