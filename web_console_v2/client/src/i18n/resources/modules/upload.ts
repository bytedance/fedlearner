import { separateLng } from 'i18n/helpers';

const upload = {
  placeholder: { zh: '点击或拖拽文件到此处上传' },
  hint: { zh: '请上传{{fileTypes}}格式文件，大小不超过{{maxSize}}MB' },
  hint_without_file_size_limit: { zh: '请上传{{fileTypes}}格式文件' },
  hint_over_file_size_limit: { zh: '大小不超过{{maxSize}}MB!' },
  label_upload: { zh: '上传', en: 'Upload' },
  msg_upload_fail: { zh: '{{fileName}} 上传失败', en: '{{fileName}} upload file' },
};

export default separateLng(upload);
