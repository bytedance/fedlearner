import { separateLng } from 'i18n/helpers';

const login = {
  slogan: { zh: '标语占位', en: 'SLOGAN HERE' },
  form_title: { zh: '账号登录', en: 'Sign in' },
  username_message: { zh: '请输入用户名!', en: 'Please enter username!' },
  username_placeholder: { zh: '用户名/邮箱', en: 'Username / Phone number' },
  password_message: { zh: '请输入密码!', en: 'Please enter password!' },
  password_placeholder: { zh: '密码', en: 'Password' },
  remember: { zh: '记住登录状态', en: 'Remember me' },
  button: { zh: '登录', en: 'Sign in' },
  aggrement: {
    zh: '登录即表示同意 {{- terms}} 和 {{privacy}}',
    en: 'I accept and agree {{terms}} and {{privacy}}',
  },
};

export default separateLng(login);
