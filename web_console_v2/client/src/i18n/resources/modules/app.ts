import { separateLng } from 'i18n/helpers';

const error = {
  go_create: { zh: '去创建' },
  help: { zh: '[WIP]查看帮助，快速了解联邦学习' },
  switch_lng: { zh: '切换语言', en: 'Language' },
  logout: { zh: '退出登录', en: 'Logout' },
  login_success: { zh: '登录成功', en: 'Login successfully' },
  copy_success: { zh: '复制成功', en: 'Copied!' },
  copy_fail: { zh: '复制失败', en: 'Copy fail!' },
  system_settings: { zh: '全局配置', en: 'Settings' },
  user_management: { zh: '用户管理', en: 'User Management' },
  audit_log: { zh: '审计日志', en: 'Audit log' },
  operation_maintenance: { zh: '运维模块', en: 'OP Module' },
  work_space: { zh: '工作台', en: 'Work Space' },
  participant: { zh: '合作伙伴', en: 'Participant' },
  coordinator: { zh: '本方', en: 'Coordinator' },
  help_document: { zh: '帮助文档', en: 'Help document' },
};

export default separateLng(error);
