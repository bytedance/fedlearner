import { separateLng } from 'i18n/helpers';

const settings = {
  label_image_ver: { zh: '镜像版本' },

  hint_update_image: { zh: '每次更新 Web Console 镜像版本后需等待一段时间，刷新页面后才可用' },

  msg_image_required: { zh: '镜像版本为必填项' },
  msg_update_success: { zh: '系统配置更新成功' },
  msg_update_wc_image: {
    zh: '已启动 Web Console 镜像更新程序，期间可能出现不可访问的情况，请等待几分钟后刷新本页面',
  },

  placeholder_image: { zh: '请选择镜像版本' },
};

export default separateLng(settings);
