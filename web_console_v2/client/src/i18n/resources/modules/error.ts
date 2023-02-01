import { separateLng } from 'i18n/helpers';

const error = {
  please_sign_in: { zh: '请登录账号', en: 'Pelase Sign in' },
  token_expired: {
    zh: '登录状态已过期，请重新登录',
    en: 'Login status has been expired, please sign in again',
  },
  unauthorized: {
    zh: '没有权限，请重新登录',
    en: 'Signature verification failed, please sign in again',
  },
  no_result: { zh: '' },
  no_tree_train_model_template: {
    zh: '找不到训练模型模板（树算法）',
    en: 'train model template(tree algorithm) not found',
  },
  no_nn_train_model_template: {
    zh: '找不到训练模型模板（nn算法）',
    en: 'train model template(nn algorithm) not found',
  },
  no_nn_horizontal_train_model_template: {
    zh: '找不到训练模型模板（横向nn算法）',
    en: 'train model template(nn horizontal algorithm) not found',
  },
  no_nn_horizontal_eval_model_template: {
    zh: '找不到模型评估模板（横向nn算法）',
    en: 'eval model template(nn horizontal algorithm) not found',
  },
  no_peer_template: {
    zh: '找不到对侧训练模型模板',
    en: 'peer train model template not found',
  },
};

export default separateLng(error);
