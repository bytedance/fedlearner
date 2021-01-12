import { separateLng } from 'i18n/helpers';

const upload = {
  placeholder: { zh: '点击或拖拽文件到此处上传' },
  hint: { zh: '请上传{{fileTypes}}格式文件，大小不超过{{maxSize}}' },
};

export default separateLng(upload);
