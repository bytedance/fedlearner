import { SettingOptions } from 'typings/settings';

const get = {
  data: {
    data: { webconsole_image: '2.0.0-rc.3' } as SettingOptions,
  },
  status: 200,
};

export const patch = {
  data: {
    data: { success: true },
  },
  status: 200,
};

export default get;
