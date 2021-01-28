import { separateLng } from 'i18n/helpers';

const error = {
  please_sign_in: { zh: '请登录账号', en: 'Pelase Sign in' },
  token_expired: {
    zh: '登录状态已过期，请重新登录',
    en: 'Login status has been expired, please sign in again',
  },
  no_result: { zh: '' },
};

export default separateLng(error);
