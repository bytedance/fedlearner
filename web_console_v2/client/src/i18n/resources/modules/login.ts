import { separateLng } from 'i18n/helpers';

const login = {
  slogan: { zh: '联邦学习', en: 'Federation Learner' },
  vision: { zh: '打破数据孤岛，让数据安全“融合”建模，创造更大价值' },
  form_title: { zh: '账号登录', en: 'Sign in' },
  username_message: { zh: '请输入用户名!', en: 'Please enter username!' },
  username_placeholder: { zh: '用户名/邮箱', en: 'Username / Phone number' },
  password_message: { zh: '请输入密码!', en: 'Please enter password!' },
  password_placeholder: { zh: '密码', en: 'Password' },
  remember: { zh: '记住登录状态', en: 'Remember me' },
  button: { zh: '登录', en: 'Sign in' },
  no_account_tip: {
    zh: '如无账号，请发送申请邮件至管理员邮箱 {{email}}',
    en: "Please contact {{email}} if you don't have an account",
  },
  error_not_find_open_url: {
    zh: '找不到即将跳转的 url 信息',
    en: 'Can’t find the url information about to be redirected',
  },
  error_not_find_sso_info: {
    zh: '找不到登陆方式 {{ssoName}} 的相关信息',
    en: 'Can’t find information about login method {{ssoName}}',
  },
  error_sso_login: {
    zh: '{{ssoName}}: SSO 验证失败',
    en: '{{ssoName}}: SSO verification failed',
  },
  error_not_find_access_token: {
    zh: '在 URL query 中找不到 access_token 信息',
    en: 'Can’t find access_token information in URL query',
  },
  label_other_login_way: {
    zh: '其他登陆方式',
    en: 'Other login ways',
  },
  label_hide_other_login_way: {
    zh: '隐藏其他登陆方式',
    en: 'Hide other login ways',
  },
};

export default separateLng(login);
