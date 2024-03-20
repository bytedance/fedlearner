import { separateLng } from 'i18n/helpers';

const error = {
  go_create: { zh: '去创建' },
  help: { zh: '[WIP]查看帮助，快速了解联邦学习' },
  switch_lng: { zh: '切换语言', en: 'Language' },
  logout: { zh: '退出登录', en: 'Logout' },
  login_success: { zh: '登录成功', en: 'Login successfully' },
  copy_success: { zh: '复制成功', en: 'Copied!' },
  system_settings: { zh: '系统配置', en: 'Sttings' },
};

export default separateLng(error);
