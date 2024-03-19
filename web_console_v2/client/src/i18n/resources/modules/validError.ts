import { separateLng } from 'i18n/helpers';

const error = {
  name_invalid: {
    zh: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
    en:
      'Only support uppercase and lowercase letters, numbers, the beginning or end of Chinese, can contain "_" and "-", no more than 63 characters',
  },
  comment_invalid: {
    zh: '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 100 个字符',
    en:
      'Only support uppercase and lowercase letters, numbers, the beginning or end of Chinese, can contain "_" and "-", no more than 100 characters',
  },
  comment_length_invalid: {
    zh: '最多为 200 个字符',
    en: 'Up to 200 characters',
  },
  job_name_invalid: {
    zh: '只支持小写字母，数字开头或结尾，可包含“-”，不超过 24 个字符',
    en:
      'Only lowercase letters are supported, numbers start or end, may contain "-", and no more than 24 characters',
  },
  cpu_invalid: {
    zh: '请输入正确的格式，正确格式为 xxxm，例如: 4000m',
    en: 'Please enter the correct format, the correct format is xxxm, for example: 4000m',
  },
  memory_invalid: {
    zh: '请输入正确的格式，正确格式为 xxxGi，xxxMi，例如: 16Gi,16Mi',
    en:
      'Please enter the correct format, the correct format is xxxGi, xxxMi, for example: 16Gi,16Mi',
  },
  email_invalid: {
    zh: '请输入正确的邮箱格式',
    en: 'Please enter the correct email format',
  },
  password_invalid: {
    zh: '请输入正确的密码格式，至少包含一个字母、一个数字、一个特殊字符，且长度在8到20之间',
    en:
      'Please enter the correct password format,contain at least one letter, one number, one special character, and the length is between 8 and 20',
  },
  missing_domain_name: {
    zh: '获取本系统 domain_name 失败',
    en: 'Failed to get domain_name of this system',
  },
  empty_node_name_invalid: {
    zh: '名称不能为空',
    en: 'Name is required',
  },
  same_node_name_invalid: {
    zh: '已有重名元素',
    en: 'There is a node with the same name',
  },
  missing_dataset_id: {
    zh: '请选择数据集',
    en: 'Please select dataset, datasetId is required',
  },
  missing_model_id: {
    zh: '请选择模型',
    en: 'Please select model, modelId is required',
  },
  missing_name: {
    zh: '请输入名称',
    en: 'Please enter name',
  },
};

export default separateLng(error);
