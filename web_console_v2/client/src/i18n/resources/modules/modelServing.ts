import { separateLng } from 'i18n/helpers';

const modelServing = {
  menu_label_model_serving: { zh: '在线服务', en: 'Online serving' },

  btn_inspect_logs: { zh: '查看日志', en: 'Inspect log' },
  btn_create_model_serving: { zh: '创建服务', en: 'Create model serving' },
  btn_check: { zh: '点击校验', en: 'Check' },
  btn_send_to_peer_side: { zh: '发送至对侧', en: 'Send to peer side' },

  service_id: { zh: 'ID', en: 'ID' },
  col_state: { zh: '状态', en: 'State' },
  col_name: { zh: '名称', en: 'Name' },
  col_instance_amount: { zh: '实例数量', en: 'Instance amount' },
  col_invoke_privilege: { zh: '调用权限', en: 'Invoke privilege' },
  col_model_type: { zh: '模型类型', en: 'Model type' },
  col_model_id: { zh: '模型ID', en: 'Model ID' },
  col_model_name: { zh: '模型名称', en: 'Model name' },
  col_cpu: { zh: 'CPU', en: 'CPU' },
  col_men: { zh: '内存', en: 'Memory' },
  col_instance_id: { zh: '实例ID', en: 'Instance ID' },

  title_create_model_serving: { zh: '创建服务', en: 'Create model set' },
  title_edit_model_serving: { zh: '编辑服务', en: 'Create model set' },
  info_receiver_create_model_serving: {
    zh: '纵向模型服务仅发起方可查看调用地址和 Signature',
    en: 'Only the sender can view the call address and signature',
  },

  label_name: { zh: '在线服务名称', en: 'Name' },
  label_comment: { zh: '在线服务描述', en: 'Desc' },
  label_type: { zh: '类型', en: 'type' },
  label_model_type: { zh: '联邦类型', en: 'Create model set' },
  label_model_type_vertical: { zh: '纵向联邦', en: 'Create model set' },
  label_model_type_horizontal: { zh: '横向联邦', en: 'Create model set' },
  label_model_inference_available: { zh: '可调用', en: 'Callable' },
  label_model_inference_unavailable: { zh: '不可调用', en: 'Uncallable' },
  label_instance_spec: { zh: '实例规格', en: 'Instance Specifications' },
  label_instance_amount: { zh: '实例数', en: 'Instance amount' },
  label_local_model_feature: { zh: '本测入模特征', en: 'Local model feature' },
  label_local_center_result: { zh: '本侧中间结果', en: 'Local center result' },
  label_peer_center_result: { zh: '对侧中间结果', en: 'Local center result' },
  label_feature_dataset: { zh: '特征数据集', en: 'Feature dataset' },
  label_model_set: { zh: '模型集', en: 'Model Set' },
  label_model: { zh: '模型', en: 'Model' },
  label_tab_user_guide: { zh: '调用指南', en: 'User guide' },
  label_tab_instance_list: { zh: '实例列表', en: 'Instance list' },
  label_input_params: { zh: '输入参数（仅本侧）', en: 'Input params' },
  label_output_params: { zh: '输出参数', en: 'Output params' },
  label_api_url: { zh: '访问地址', en: 'API URL' },
  label_local_feature: { zh: '本侧特征', en: 'Local feature' },
  label_signature: { zh: 'Signature', en: 'Signature' },

  placeholder_searchbox_name: { zh: '请输入名称查询', en: 'Please input name' },
  placeholder_name: { zh: '请输入在线服务名称', en: 'Please input online serving name' },
  placeholder_input: { zh: '请输入', en: 'Please input' },
  placeholder_select: { zh: '请选择', en: 'Please select' },
  placeholder_select_model: { zh: '请选择模型', en: 'Please select model' },
  placeholder_comment: {
    zh: '最多为 200 个字符',
    en: 'Up to 200 characters',
  },

  msg_required: { zh: '必填项', en: 'Required' },
  msg_check_fail: {
    zh: '请输入正确的特征、中间结果或特征数据集',
    en: 'Please enter the correct feature, intermediate result or feature data set',
  },

  msg_title_confirm_delete: { zh: '确认要删除「{{name}}」？', en: 'Confirm to delete <{{name}}>?' },
  msg_content_confirm_delete: {
    zh: '一旦删除，在线服务相关数据将无法复原，请谨慎操作',
    en: 'The delete operation cannot be recovered, please operate with caution',
  },
  msg_edit_service_desc: { zh: '在线服务信息', en: 'Service Info' },

  tip_local_feature: {
    zh: '请正确选择本侧特征，特征选择会影响推理结果',
    en:
      'Please select the local feature correctly, the feature selection will affect the inference result',
  },
  tip_instance_range: {
    zh: '实例数范围1～100',
    en: 'The number of instances ranges from 1 to 100',
  },

  state_loading: { zh: '部署中', en: 'Loading' },
  state_unloading: { zh: '删除中', en: 'Unloading' },
  state_running: { zh: '运行中', en: 'Running' },
  state_unknown: { zh: '异常', en: 'Unknown' },
  state_pending_accept: { zh: '待合作伙伴配置', en: 'Wait for accepting' },
  state_waiting_config: { zh: '待合作伙伴配置', en: 'Wait for config' },
  state_deleted: { zh: '异常', en: 'deleted' },
  tip_deleted: { zh: '对侧已经删除', en: 'Another side has been deleted' },

  state_check_waiting: { zh: '待校验', en: 'Waiting' },
  state_check_success: { zh: '校验成功', en: 'Success' },
  state_check_fail: { zh: '校验不通过', en: 'Fail' },

  cannot_create_service_without_models: {
    zh: '因对应模型不存在，请选择两侧均存在的纵向联邦模型进行部署',
    en:
      'Because there is no deployment of the corresponding model, please reselect the longitudinal federal model that exists on both sides.',
  },

  msg_todo_model_serving_tasks: {
    zh: '{{count}} 条待处理在线服务',
    en: '{{count}} tasks to be processed',
  },

  msg_title_todo_model_serving_tasks: {
    zh: '待处理在线服务',
    en: 'Tasks to be processed',
  },

  msg_suffix_model_serving_tasks: {
    zh: ' 的在线任务',
    en: "'s service",
  },
  msg_duplicate_service_name: {
    zh: '在线服务名称已存在',
    en: 'Service name already exists',
  },
  msg_duplicate_participant_service_name: {
    zh: '合作伙伴侧在线服务名称已存在',
    en: 'service name already exists on the participant side',
  },
};

export default separateLng(modelServing);
