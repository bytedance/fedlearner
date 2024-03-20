import { separateLng } from 'i18n/helpers';

const menu = {
  label_project: { zh: '项目管理', en: 'Projects' },
  label_workflow: { zh: '工作流管理', en: 'Workflows' },
  label_workflow_tpl: { zh: '模板管理', en: 'Workflow templates' },
  label_datasets: { zh: '数据集管理', en: 'Datasets' },
  label_datasets_training: { zh: '训练数据集管理', en: 'Training datasets' },
  label_datasets_test: { zh: '测试数据集', en: 'Test datasets' },
  label_datasets_predict: { zh: '预测数据集', en: 'Predict datasets' },
  label_settings: { zh: '系统配置', en: 'Settings' },
  label_users: { zh: '用户管理', en: 'User Management' },
};

export default separateLng(menu);
