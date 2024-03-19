import { SettingOptions } from 'typings/settings';
import { variables } from './examples';

const get = {
  data: {
    data: {
      webconsole_image: '2.0.0-rc.3',
      variables,
    } as SettingOptions,
    status: 200,
  },
};

export const patch = {
  data: {
    data: {
      webconsole_image: '2.0.0-rc.3',
      variables,
    } as SettingOptions,
  },
  status: 200,
};

export default get;
