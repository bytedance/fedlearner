import { separateLng } from 'i18n/helpers';

const settings = {
  label_image_ver: { zh: '镜像版本' },

  hint_update_image: { zh: '每次更新 Web Console 镜像版本后需等待一段时间，刷新页面后才可用' },

  msg_image_required: { zh: '镜像版本为必填项' },
  msg_update_success: { zh: '系统配置更新成功' },
  msg_update_wc_image: {
    zh:
      '已启动更新程序，Pod 开始进行替换，完成后可能需要手动 Port forward，并且该窗口将在几分钟后变得不可用。',
  },

  placeholder_image: { zh: '请选择镜像版本' },
  system_log: { zh: '系统日志', en: 'System log' },
  system_setting: { zh: '全局配置', en: 'Settings' },
  edit_success: { zh: '修改环境变量成功', en: 'Edit environment variables succeed!' },

  msg_wrong_format: { zh: 'JSON {{type}} 格式错误', en: 'JSON {{type}} wrong format' },
};

export default separateLng(settings);
