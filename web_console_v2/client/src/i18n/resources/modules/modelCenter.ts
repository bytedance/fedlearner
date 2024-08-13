import { separateLng } from 'i18n/helpers';

const modelCenter = {
  menu_label_model_management: { zh: '模型管理', en: 'Model management' },
  menu_label_model_evaluation: { zh: '模型评估', en: 'Model evaluation' },
  menu_label_offline_prediction: { zh: '离线预测', en: 'Offline prediction' },
  menu_label_algorithm_management: { zh: '算法管理', en: 'Algorithm management' },

  label_tab_model_set: { zh: '模型集', en: 'Model Set' },
  label_tab_model_favourit: { zh: '我的收藏', en: 'My favourit model' },
  label_tab_my_algorithm: { zh: '我的算法', en: 'My algorithm' },
  label_tab_my_built_in: { zh: '预置算法', en: 'Built-in algorithm' },
  label_tab_model_evaluation: { zh: '模型评估', en: 'Model evaluation' },
  label_tab_model_compare: { zh: '模型对比', en: 'Model compare' },

  label_tab_algorithm_preview: { zh: '算法预览', en: 'Algorithm preview' },
  label_tab_change_log: { zh: '变更记录', en: 'Change log' },

  label_algorithm_params: { zh: '超参数', en: 'algorithm params' },
  label_algorithm_params_name: { zh: '名称', en: 'name' },
  label_algorithm_params_value: { zh: '默认值', en: 'default value' },
  label_algorithm_params_required: { zh: '是否必填', en: 'required' },
  label_algorithm_params_comment: { zh: '提示语(必填)', en: 'comment' },
  label_algorithm_add_params: { zh: '新增超参数', en: 'add new param' },
  placeholder_algorithm_params_name: {
    zh: '请输入参数名称',
    en: 'Please input the name of params',
  },
  placeholder_algorithm_params_value: { zh: '请输入默认值', en: 'Please input the default value' },
  placeholder_algorithm_params_comment: { zh: '请输入提示语', en: 'Please input comment' },

  msg_todo_train_tasks: { zh: '{{count}} 条待处理训练任务' },
  msg_todo_model_job_tasks: { zh: '{{count}} 条待处理模型训练' },
  msg_todo_evaluation_tasks: { zh: '{{count}} 条待处理评估任务' },
  msg_todo_prediction_tasks: { zh: '{{count}} 条待处理预测任务' },
  msg_todo_algorithm_tasks: { zh: '{{count}} 条待处理算法任务' },
  msg_before_revoke_authorize: {
    zh: '撤销授权后，发起方不可运行模型训练，正在运行的任务不受影响',
    en:
      'After revoking authorization, the initiator cannot run the model training, and the running task will not be affected',
  },
  msg_before_authorize: {
    zh: '授权后，发起方可以运行模型训练',
    en: 'After authorization, the initiator can run the model training',
  },

  btn_create_model_set: { zh: '创建模型集', en: 'Create model set' },
  btn_create_model_job: { zh: '创建训练', en: 'Create model job' },
  btn_train_model: { zh: '发起训练', en: 'Start train' },
  btn_evaluation: { zh: '创建评估', en: 'Start evaluation' },
  btn_inspect_logs: { zh: '查看日志', en: 'Inspect log' },
  btn_restart: { zh: '重新发起', en: 'Restart' },
  btn_parameter_tuning: { zh: '调参', en: 'Parameter tuning' },
  btn_prediction: { zh: '创建预测', en: 'Start prediction' },
  btn_create_algorithm: { zh: '创建算法', en: 'Create algorithm' },
  btn_create_type: { zh: '新增类型', en: 'Create type' },
  btn_start_model: { zh: '开始训练', en: 'Start train' },
  btn_submit: { zh: '提交', en: 'Submit' },
  btn_compare: { zh: '发起对比', en: 'Start compare' },
  btn_create_compare_report: { zh: '创建对比报告', en: 'Create compare report' },
  btn_go_back_to_index_page: { zh: '回到首页', en: 'Go back to index page' },
  btn_start_new_job: { zh: '发起新任务', en: 'Start new job' },
  btn_submit_and_send_request: { zh: '提交并发送', en: 'Submit and send request' },
  btn_confirm_authorized: { zh: '确认授权', en: 'Confirm authorized' },
  btn_save_edit: { zh: '保存编辑', en: 'Save' },
  btn_next_step: { zh: '下一步', en: 'Next step' },
  btn_stop: {
    zh: '终止',
    en: 'Stop',
  },
  btn_cancel: {
    zh: '取消',
    en: 'cancel',
  },
  btn_terminal: {
    zh: '终止',
    en: 'terminal',
  },

  placeholder_searchbox_model: { zh: '输入模型名称', en: 'Please input model name' },
  placeholder_searchbox_model_set: { zh: '输入模型集名称', en: 'Please input model set name' },
  placeholder_searchbox_model_job: {
    zh: '输入模型训练名称',
    en: 'Please input model job name',
  },
  placeholder_searchbox_evaluation_report: {
    zh: '输入评估任务名称',
    en: 'Please input evaluation task name',
  },
  placeholder_searchbox_prediction_report: {
    zh: '输入预测任务名称',
    en: 'Please input prediction task name',
  },
  placeholder_searchbox_algorithm: { zh: '输入算法名称', en: 'Please input algorithm name' },

  placeholder_input_algorithm_type: { zh: '请输入算法类型', en: 'Please input algorithm type' },
  placeholder_searchbox_model_file: {
    zh: '输入目标地址，搜索模型文件',
    en: 'Input the target address, search for model files',
  },
  placeholder_searchbox_compare_report: {
    zh: '输入对比报告名称',
    en: 'Please input report name',
  },
  placeholder_searchbox_evaluation_model: {
    zh: '输入关键词',
    en: 'Please input name',
  },

  col_model_set_name: { zh: '模型集名称', en: 'Model set name' },
  col_algorithm: { zh: '算法', en: 'algorithm' },
  col_new_version: { zh: '最新版本', en: 'version' },
  col_comment: { zh: '{{name}}描述', en: '{{name}} comment' },
  col_model_name: { zh: '模型名称', en: 'Model name' },
  col_model_id: { zh: '模型ID', en: 'Model ID' },
  col_data_set: { zh: '数据集', en: 'dataset' },
  col_evaluation_task_name: { zh: '评估任务名称', en: 'Evaluation task name' },
  col_state: { zh: '运行状态', en: 'State' },
  col_evaluation_target: { zh: '评估对象', en: 'Evaluation target' },
  col_prediction_target: { zh: '预测对象', en: 'Prediction target' },
  col_prediction_task_name: { zh: '预测任务名称', en: 'Prediction task name' },
  col_name: { zh: '名称', en: 'Name' },
  col_type: { zh: '类型', en: 'Type' },
  col_compare_report_name: { zh: '对比报告名称', en: 'Compare report name' },
  col_compare_number: { zh: '对比项', en: 'Compare number' },
  col_model_type: { zh: '模型类型', en: 'Model type' },
  col_model_source: { zh: '模型来源', en: 'Model source' },
  col_creator: { zh: '创建者', en: 'creator' },
  col_initiator: { zh: '发起方', en: 'initiator' },
  col_authorized: { zh: '授权状态', en: 'authorized' },
  col_loca_authorized: { zh: '本侧授权状态', en: 'local authorized' },
  col_federal_type: { zh: '联邦类型', en: 'federal type' },
  col_total_jobs: { zh: '任务总数', en: 'total jobs' },
  col_latest_job_state: { zh: '最新任务状态', en: 'latest job state' },
  col_job_state: { zh: '任务状态', en: 'job state' },
  col_running_time: { zh: '运行时长', en: 'runtime' },
  col_start_time: { zh: '开始时间', en: 'start time' },
  col_stop_time: { zh: '结束时间', en: 'end time' },
  col_running_param: { zh: '运行参数', en: 'running param' },

  title_create_model_set: { zh: '创建模型集', en: 'Create model set' },
  title_edit_model_set: { zh: '编辑模型集', en: 'Edit model set' },
  title_create_model_job: { zh: '创建训练', en: 'Create model job' },
  title_edit_model_train: { zh: '编辑训练', en: 'Edit model train' },
  title_start_new_job: { zh: '发起新任务', en: 'Start new job' },
  title_auth_model_train: { zh: '授权模型训练', en: '授权模型训练' },
  title_create_valuation: { zh: '创建评估', en: 'Create Evaluation' },
  title_create_prediction: { zh: '创建预测', en: 'Create Prediction' },

  title_edit_model: { zh: '编辑模型', en: 'Edit model' },
  title_image_version: { zh: '镜像参数', en: 'Image params' },
  title_algorithm_config: { zh: '算法配置', en: 'Algorithm config' },
  title_train_info: { zh: '训练信息', en: 'Train information' },
  title_resource_config_detail: { zh: '资源配置参数详情', en: 'Resource config detail' },
  title_resource_config: { zh: '资源配置', en: 'Resource config' },
  title_advanced_config: { zh: '高级配置', en: 'Advanced config' },
  title_model_favourit: { zh: '我的收藏', en: 'My favourit model' },
  title_revision_history: { zh: '历史版本', en: 'Revision history' },
  title_base_info: { zh: '基本信息', en: 'Base info' },
  title_train_config: { zh: '训练配置', en: 'Train config' },
  title_train_report: { zh: '训练报告', en: 'Train report' },
  title_instance_info: { zh: '实例信息', en: 'Instance info' },
  title_version: { zh: '版本', en: 'Version' },
  title_model_train_dataset: { zh: '训练数据集', en: 'Train dataset' },
  title_train_duration: { zh: '训练时间', en: 'Train duration' },
  title_log: { zh: '日志', en: 'Log' },
  title_check: { zh: '查看', en: 'Check' },
  title_model_comment: { zh: '模型描述', en: 'Model comment' },
  title_indicator_auc_roc: { zh: 'AUC ROC', en: 'AUC ROC' },
  title_indicator_accuracy: { zh: 'Accuracy', en: 'Accuracy' },
  title_indicator_precision: { zh: 'Precision', en: 'Precision' },
  title_indicator_recall: { zh: 'Recall', en: 'Recall' },
  title_indicator_f1_score: { zh: 'F1 score', en: 'F1 score' },
  title_indicator_log_loss: { zh: 'log loss', en: 'log loss' },
  title_confusion_matrix: { zh: 'Confusion Matrix', en: 'Confusion Matrix' },
  title_confusion_matrix_normalization: { zh: '归一化', en: 'Normalization' },
  title_feature_importance: {
    zh: 'Feature Importance（Top 15）',
    en: 'Feature Importance（Top 15）',
  },
  title_export_model: {
    zh: '导出模型',
    en: 'export model',
  },
  title_export_evaluation_report: {
    zh: '导出评估报告',
    en: 'export evaluation report',
  },
  title_export_prediction_report: {
    zh: '导出预测报告',
    en: 'export prediction report',
  },
  title_export_compare_report: {
    zh: '导出对比报告',
    en: 'export compare report',
  },
  title_export_dataset: {
    zh: '导出数据集',
    en: 'export dataset',
  },
  title_evaluation_target: { zh: '评估对象', en: 'Evaluation target' },
  title_evaluation_report: { zh: '评估报告', en: 'Evaluation report' },
  title_prediction_report: { zh: '预测报告', en: 'Prediction report' },
  title_prediction_result: { zh: '预测结果', en: 'Prediction result' },
  title_evaluation_result: { zh: '评估结果', en: 'Evaluation result' },
  title_compare_report: { zh: '对比报告', en: 'Compare report' },
  title_result_dataset: { zh: '结果数据集', en: 'Result dataset' },

  title_create_algorithm: { zh: '创建我的算法', en: 'Create algorithm' },
  title_edit_algorithm: { zh: '编辑算法', en: 'Edit algorithm' },
  title_algorithm_file: { zh: '算法文件', en: 'Algorithm file' },
  title_algorithm_label_owner: { zh: '算法文件 - 标签所有者', en: 'Algorithm file - label owner' },
  title_algorithm_no_label_owner: {
    zh: '算法文件 - 非标签所有者',
    en: 'Algorithm file - no label owner',
  },
  title_todo_train_tasks: { zh: '待处理训练任务', en: 'waiting train model task' },
  title_todo_model_job_tasks: { zh: '待处理模型训练', en: 'waiting model job task' },
  title_todo_prediction_tasks: { zh: '待处理预测任务', en: 'waiting prediction model task' },
  title_todo_evaluation_tasks: { zh: '待处理评估任务', en: 'waiting evaluation model task' },
  title_todo_algorithm_tasks: { zh: '待处理算法任务', en: 'waiting algorithm model task' },
  title_create_compare_report: { zh: '创建对比报告', en: 'Create compare report' },

  title_reject_application: { zh: '拒绝申请', en: 'Reject application' },

  title_label_owner: { zh: '标签所有者', en: 'Label owner' },
  title_no_label_owner: {
    zh: '非标签所有者',
    en: 'No label owner',
  },
  title_train_model: {
    zh: '模型训练',
    en: 'Train Model',
  },
  title_algorithm_audit: {
    zh: '算法审核',
    en: 'Algorithm audit',
  },
  title_authorization_request: {
    zh: '{{peerName}}向您发起「{{name}}」训练授权申请',
    en: '{{peerName}} initiates a training authorization application for "{{name}}"',
  },
  title_train_model_job: {
    zh: '训练任务',
    en: 'Train model job',
  },
  title_train_job_compare: {
    zh: '训练任务对比',
    en: 'Train job compare',
  },

  label_model_set: { zh: '模型集', en: 'Model Set' },
  label_model: { zh: '模型', en: 'Model' },
  title_model_set_info: { zh: '模型集信息', en: 'Model set info' },
  title_model_info: { zh: '模型信息', en: 'Model info' },
  label_data_set: { zh: '数据集', en: 'dataset' },
  label_intersection_set: { zh: '数据集', en: 'dataset' },
  label_data_source: { zh: '数据源', en: 'data source' },
  label_data_path: { zh: '数据源', en: 'data source' },
  label_manual_datasource: { zh: '手动输入数据源', en: 'Manually entering the data source' },

  label_model_set_name: { zh: '模型集名称', en: 'Model set name' },
  label_model_set_comment: { zh: '模型集描述', en: 'Model set comment' },
  label_model_name: { zh: '模型名称', en: 'Model name' },
  label_model_comment: { zh: '模型描述', en: 'Model comment' },
  label_model_train_dataset: { zh: '训练数据集', en: 'Train dataset' },
  label_model_train_comment: { zh: '模型描述', en: 'Train comment' },
  label_resource_template: { zh: '资源模板', en: 'Resource template' },

  label_image: { zh: '镜像', en: 'Image' },

  label_file_ext: { zh: '文件扩展名', en: 'File extension' },
  label_file_type: { zh: '文件类型', en: 'File type' },
  label_enable_packing: { zh: '是否优化', en: 'Enable packing' },
  label_ignore_fields: { zh: '忽略字段', en: 'Ignore fields' },
  label_cat_fields: { zh: '类型变量字段', en: 'Categorical fields' },
  label_send_metrics_to_follower: {
    zh: '是否将指标发送至 follower',
    en: 'send_metrics_to_follower',
  },
  label_send_scores_to_follower: {
    zh: '是否将预测值发送至 follower',
    en: 'send_scores_to_follower',
  },
  label_verbosity: { zh: '日志输出等级', en: 'Verbosity' },
  label_label_field: { zh: '标签字段', en: 'Label field' },
  label_load_model_path: { zh: '加载模型路径', en: 'Load model path' },
  label_load_model_name: { zh: '加载模型名称', en: 'Load model name' },
  label_load_checkpoint_filename: { zh: '加载文件名', en: 'Load checkpoint filename' },
  label_load_checkpoint_filename_with_path: {
    zh: '加载文件路径',
    en: 'Load checkpoint filename with path',
  },
  label_verify_example_ids: { zh: '是否检验 example_ids', en: 'verify_example_ids' },
  label_no_data: { zh: '标签方是否无特征', en: 'no_data' },
  label_role: { zh: '训练角色', en: 'Training role' },
  label_steps_per_sync: { zh: '参数同步 step 间隔', en: 'Steps per sync' },
  label_image_version: { zh: '镜像版本号', en: 'image_version' },
  label_num_partitions: { zh: 'num_partitions', en: 'num_partitions' },
  label_shuffle_data_block: { zh: '是否打乱顺序', en: 'shuffle_data_block' },

  label_train_name: { zh: '训练名称', en: 'Train name' },
  label_federal_type: { zh: '联邦类型', en: 'Federal type' },
  label_train_role_type: { zh: '训练角色', en: 'Train role type' },
  label_radio_logistic: { zh: 'logistic', en: 'logistic' },
  label_radio_mse: { zh: 'mse', en: 'mse' },
  label_param_config: { zh: '参数配置', en: 'Params config' },

  label_choose_algorithm: { zh: '选择算法', en: 'Choose algorithm' },
  label_algorithm: { zh: '算法', en: 'Algorithm' },
  label_role_type: { zh: '角色', en: 'Role type' },
  label_loss_type: { zh: '损失函数类型', en: 'Loss type' },
  label_radio_label: { zh: '标签方', en: 'Label' },
  label_radio_feature: { zh: '特征方', en: 'Feature' },
  label_learning_rate: { zh: '学习率', en: 'learning_rate' },
  label_max_iters: { zh: '迭代数', en: 'max_iters' },
  label_max_depth: { zh: '最大深度', en: 'max_depth' },
  label_l2_regularization: { zh: 'L2惩罚系数', en: 'l2_regularization' },
  label_max_bins: { zh: '最大分箱数量', en: 'max_bins' },
  label_code_tar: { zh: '代码', en: 'code_tar' },
  label_num_parallel: { zh: '线程池大小', en: 'num_parallel' },
  label_validation_data_path: { zh: '验证数据集地址', en: 'validation_data_path' },

  label_epoch_num: { zh: 'epoch_num', en: 'epoch_num' },
  label_sparse_estimator: { zh: 'sparse_estimator', en: 'sparse_estimator' },
  label_save_checkpoint_steps: { zh: '保存备份间隔步数', en: 'save_checkpoint_steps' },
  label_save_checkpoint_secs: { zh: '保存备份间隔秒数', en: 'save_checkpoint_secs' },
  label_optimize_target: { zh: '训练目标', en: 'Train target' },
  label_model_feature: { zh: '不入模特征', en: 'Model feature' },

  label_resource_template_type: { zh: '资源模板', en: 'Resource template' },
  label_radio_high: { zh: '大', en: 'High' },
  label_radio_medium: { zh: '中', en: 'Medium' },
  label_radio_low: { zh: '小', en: 'Low' },
  label_radio_custom: { zh: '自定义', en: 'Custom' },

  label_master_replicas: { zh: 'Master 实例数', en: 'master_replicas' },
  label_master_cpu: { zh: 'Master CPU数量', en: 'master_cpu' },
  label_master_mem: { zh: 'Master内存大小', en: 'master_mem' },
  label_ps_replicas: { zh: 'PS 实例数', en: 'ps_replicas' },
  label_ps_cpu: { zh: 'PS CPU数量', en: 'ps_cpu' },
  label_ps_mem: { zh: 'PS内存大小', en: 'ps_mem' },
  label_ps_num: { zh: 'PS数量', en: 'ps_num' },
  label_worker_replicas: { zh: 'Worker 实例数', en: 'worker_replicas' },
  label_worker_cpu: { zh: 'Worker CPU数量', en: 'worker_cpu' },
  label_worker_mem: { zh: 'Worker内存大小', en: 'worker_mem' },
  label_worker_num: { zh: 'Worker数量', en: 'worker_num' },

  label_is_share_model_evaluation_index: {
    zh: '共享模型评价指标',
    en: 'Share model evaluation index',
  },
  label_is_share_model_evaluation_report: {
    zh: '共享模型评价报告',
    en: 'Share model evaluation report',
  },
  label_is_share_offline_prediction_result: {
    zh: '共享离线预测结果',
    en: 'Share offline prediction result',
  },
  label_is_allow_coordinator_parameter_tuning: {
    zh: '允许合作伙伴自行发起调参任务',
    en: 'Allow coordinator to initiate tuning tasks on their own',
  },
  label_is_auto_create_compare_report: {
    zh: '自动生成对比报告',
    en: 'Auto create compare report',
  },

  label_model_version: { zh: '版本列表', en: 'Model version' },
  label_model_version_count: { zh: '共{{count}}个', en: '{{count}} item' },

  label_score_threshold: { zh: 'Score threshold = {{number}}', en: 'Score threshold = {{number}}' },

  label_download_model_package: {
    zh: '下载模型包',
    en: 'Download model package',
  },
  label_download_evaluation_report: {
    zh: '下载评估任务',
    en: 'Download evaluation report',
  },
  label_download_prediction_report: {
    zh: '下载预测报告',
    en: 'Download prediction report',
  },
  label_download_compare_report: {
    zh: '下载对比报告',
    en: 'Download compare report',
  },

  label_evaluation_task_name: { zh: '评估任务名称', en: 'Evaluation task name' },
  label_evaluation_dataset: { zh: '评估数据集', en: 'Evaluation dataset' },
  label_evaluation_comment: { zh: '评估任务描述', en: 'Comment' },
  label_prediction_task_name: { zh: '预测任务名称', en: 'Prediction task name' },
  label_prediction_dataset: { zh: '预测数据集', en: 'Prediction dataset' },
  label_prediction_comment: { zh: '预测任务描述', en: 'Comment' },

  label_algorithm_name: { zh: '算法名称', en: 'Algorithm name' },
  label_algorithm_type: { zh: '算法类型', en: 'Algorithm type' },
  label_type: { zh: '类型', en: 'Type' },
  label_federation_type: { zh: '联邦方式', en: 'Federation type' },
  label_import_type: { zh: '导入方式', en: 'Import type' },
  label_algorithm_file_path: { zh: '算法文件路径', en: 'Algorithm file path' },
  label_select_from_local_file: { zh: '从本地文件中选择', en: 'Select from local file' },
  label_radio_cross_sample: { zh: '跨样本', en: 'Cross sample' },
  label_radio_cross_feature: { zh: '跨特征', en: 'Cross feature' },
  label_radio_path_import: { zh: '路径导入', en: 'Path import' },
  label_radio_local_import: { zh: '本地导入', en: 'local import' },
  label_algorithm_type_tree_model: { zh: '树模型', en: 'Tree model' },
  label_algorithm_type_nn_model: { zh: 'NN模型', en: 'NN model' },

  label_role_type_leader: { zh: 'leader', en: 'Leader' },
  label_role_type_follower: { zh: 'follower', en: 'Follower' },

  label_name: { zh: '名称', en: 'name' },
  label_comment: { zh: '描述', en: 'desc' },
  label_reject_reason: { zh: '拒绝申请', en: 'reject reaso' },
  label_pass: { zh: '已通过申请', en: 'Application passed' },
  label_reject: { zh: '已拒绝申请', en: 'Application rejected' },

  label_start_task: { zh: ' 发起了', en: ' start' },
  label_stopped_at: { zh: '结束时间', en: 'Stopped at' },
  label_started_at: { zh: '开始时间', en: 'Started at' },
  label_output_model: { zh: '输出模型', en: 'Exported model' },

  suffix_train_tasks: { zh: '的训练任务', en: 'train task' },
  suffix_model_job_tasks: { zh: '的模型训练', en: 'model job task' },
  suffix_prediction_tasks: { zh: '的预测任务', en: 'prediction task' },
  suffix_evaluation_tasks: { zh: '的评估任务', en: 'evaluation task' },
  suffix_algorithm_tasks: { zh: '的算法任务', en: 'algorithm task' },

  suffix_go_back_to_index: {
    zh: '{{time}}S 后自动回到首页',
    en: 'After {{time}}S,go back to index',
  },

  placeholder_model_set_name: { zh: '请输入模型集名称', en: 'Please input' },
  placeholder_model_set_comment: {
    zh: '支持1～100位可见字符，且只包含大小写字母、中文、数字、中划线、下划线',
    en:
      'Supports 1-100 visible characters, and only contains uppercase and lowercase letters, Chinese characters, numbers, underscores, and underscores',
  },
  placeholder_model_name: { zh: '请填写', en: 'Please input' },
  placeholder_model_train_dataset: { zh: '请选择', en: 'Please select' },
  placeholder_model_train_comment: {
    zh: '支持1～100位可见字符，且只包含大小写字母、中文、数字、中划线、下划线',
    en:
      'Supports 1-100 visible characters, and only contains uppercase and lowercase letters, Chinese characters, numbers, underscores, and underscores',
  },
  placeholder_input: { zh: '请填写', en: 'Please input' },
  placeholder_select: { zh: '请选择', en: 'Please select' },
  placeholder_comment: {
    zh: '最多为 200 个字符',
    en: 'Up to 200 characters',
  },
  placeholder_data_source: { zh: '请输入数据源', en: 'Please input dataSource' },

  msg_model_set_name_required: { zh: '模型集名称为必填项', en: 'Model set name is required' },
  msg_model_name_required: { zh: '模型名称为必填项', en: 'Model name is required' },
  msg_model_train_dataset: { zh: '训练数据集为必填项', en: 'Train dataset is required' },
  msg_required: { zh: '必填项', en: 'Required' },
  msg_modify_model_name_success: { zh: '修改模型名称成功', en: 'Modify model name success' },
  msg_modify_model_comment_success: { zh: '修改模型描述成功', en: 'Modify model comment success' },
  msg_delete_model_success: { zh: '删除模型成功', en: 'Delete model success' },
  msg_file_required: { zh: '请上传文件', en: 'Please upload file' },
  msg_quit_train_model_title: {
    zh: '确认要退出「发起模型训练流程」？',
    en: 'Are you sure you want to exit the "Initiate Model Training Process"?',
  },
  msg_quit_train_model_content: {
    zh: '退出后，当前所填写的信息将被清空。',
    en: 'After logging out, the information currently filled in will be cleared.',
  },
  msg_quit_evaluation_model_title: {
    zh: '确认要退出「{{name}}」？',
    en: 'Are you sure you want to exit the "{{name}}"?',
  },
  msg_quit_prediction_model_title: {
    zh: '确认要退出「{{name}}」？',
    en: 'Are you sure you want to exit the "{{name}}"?',
  },
  msg_quit_form_create: {
    zh: '确认要退出？',
    en: 'Are you sure you want to exit the "{{name}}"?',
  },
  msg_quit_form_edit: {
    zh: '确认要退出编辑「{{name}}」？',
    en: 'Are you sure you want to exit the "{{name}}" editing?',
  },

  msg_please_select_evaluation_target: {
    zh: '请选择评估对象',
    en: 'Please select evaluation target',
  },
  msg_model_compare_count_limit: {
    zh: '至少{{min}}个，至多{{max}}个评估对象',
    en: 'At least {{min}} and at most {{max}} evaluation target for compare',
  },
  msg_title_confirm_delete_model: {
    zh: '确认要删除该模型吗？',
    en: 'Are you sure you want to delete the model?',
  },
  msg_content_confirm_delete_model: {
    zh: '删除后，不影响正在使用该模型的任务，使用该模型的历史任务不能再正常运行，请谨慎删除',
    en:
      'After deleting, it will not affect the tasks that are using the model, and the historical tasks using the model can no longer run normally, please delete with caution',
  },
  msg_create_model_job_success: {
    zh: '创建成功，等待合作伙伴授权',
    en: 'Created successfully, waiting for partner authorization',
  },
  msg_create_model_job_success_peer: {
    zh: '授权完成，等待合作伙伴运行',
    en: 'Authorized successfully, waiting for partner run',
  },
  msg_create_evaluation_job_success_peer: {
    zh: '已授权模型评估，任务开始运行',
    en: 'Model evaluation has been authorized, task starts to run',
  },
  msg_edit_model_job_success: {
    zh: '保存成功',
    en: 'Save success',
  },
  msg_launch_model_job_success: {
    zh: '发起成功',
    en: 'Launch success',
  },
  msg_launch_model_job_no_peer_auth: {
    zh: '合作伙伴未授权，不能发起新任务',
    en: 'The partner is not authorized to launch a new task',
  },
  msg_stop_model_job_success: {
    zh: '终止成功',
    en: 'Stop model job success',
  },
  msg_title_confirm_delete_model_job_group: {
    zh: '确认要删除「{{name}}」？',
    en: 'Are you sure you want to delete "{{name}}"?',
  },
  msg_content_confirm_delete_model_job_group: {
    zh: '删除后，该模型训练下的所有信息无法复原，请谨慎操作',
    en:
      'After deletion, all information under the model training cannot be recovered, please operate with caution',
  },
  msg_can_not_edit_peer_config: {
    zh: '合作伙伴未授权，不能编辑合作伙伴配置',
    en: 'The partner is not authorized to edit the partner configuration',
  },
  msg_stop_warnning: {
    zh: '确认要终止「{{name}}」？',
    en: 'Are you sure to stop {{name}}',
  },
  msg_stop_warning_text: {
    zh: '终止后，该评估任务将无法重新运行，请谨慎操作',
    en: 'After stopping, the evaluation task will not be able to run again. Please be careful.',
  },
  msg_stop_successful: {
    zh: '终止成功',
    en: 'Stop Successful',
  },
  msg_delete_warnning: {
    zh: '确认要删除「{{name}}」？',
    en: 'Are you sure to delete {{name}}',
  },
  msg_delete_evaluation_warning_text: {
    zh: '删除后，该评估任务及信息将无法恢复，请谨慎操作',
    en:
      'After deleting, the evaluation task and information will not be able to recover. Please be careful.',
  },
  msg_delete_prediction_warning_text: {
    zh: '删除后，该预测任务及信息将无法恢复，请谨慎操作',
    en:
      'After deleting, the prediction task and information will not be able to recover. Please be careful.',
  },
  msg_evaluation_invitation_text: {
    zh: '向您发起「{{name}}」的模型评估授权申请',
    en: 'invites you to evaluate the model "{{name}}"',
  },
  msg_prediction_invitation_text: {
    zh: '向您发起「{{name}}」的离线预测授权申请',
    en: 'invites you to predict the model "{{name}}"',
  },
  msg_target_model_not_found: {
    zh: '目标模型不存在，请联系合作伙伴重新选择',
    en: 'Target model does not exist, please contact the partner to re-select',
  },
  msg_participant_tip_text: {
    zh: '合作方均同意授权时，{{module}}任务将自动运行',
    en: 'All partners agree to authorize, {{module}} task will automatically run',
  },
  msg_time_required: { zh: '请选择时间', en: 'Set time please' },
  msg_model_job_edit_success: {
    zh: '编辑成功',
    en: 'Edit success',
  },

  hint_model_set_form_modal: {
    zh: '模型集名称和描述将同步至所有合作伙伴。',
    en: 'The model set name and description will be synchronized to all partners.',
  },
  hint_no_share_offline_prediction_result: {
    zh: '对方已选择不将预测结果分享给你',
    en: 'The other party has chosen not to share the prediction result with you',
  },
  hint_algorithm_audit: {
    zh: '请注意检查算法代码的细节，这涉及到您的信息隐私等安全问题。',
    en:
      'Please pay attention to check the details of the algorithm code, which involves security issues such as your information privacy.',
  },

  no_result: {
    zh: '暂无模型版本，请 ',
    en: 'No model , please ',
  },

  step_global: { zh: '全局配置', en: 'Global config' },
  step_param: { zh: '参数配置', en: 'Params config' },

  step_coordinator: { zh: '本侧配置', en: 'Coordinator config' },
  step_participant: { zh: '合作伙伴配置', en: 'Participant config' },

  tip_radio_logistic: { zh: '用于分类任务', en: 'For classification tasks' },
  tip_radio_mse: { zh: '用于回归任务', en: 'For regression tasks' },
  tip_choose_algorithm: {
    zh: '后续模型训练将沿用该算法，只可调整算法版本和算法参数',
    en:
      'Subsequent model training will continue to use this algorithm, and only the algorithm version and algorithm parameters can be adjusted',
  },
  tip_share_model_evaluation_index: {
    zh: '共享后合作伙伴能够获得模型训练任务相关的数据指标',
    en: 'After sharing, partners can obtain data indicators related to model training tasks',
  },
  tip_share_model_evaluation_report: {
    zh: '共享后合作伙伴能够获得模型评估任务相关的数据指标',
    en: 'After sharing, partners can obtain data indicators related to model evaluation tasks',
  },
  tip_share_offline_prediction_result: {
    zh: '确认要共享吗？合作伙伴将获得离线预测结果，请注意风险。',
    en:
      'Are you sure you want to share? Partners will get offline prediction results, please be aware of risks.',
  },
  tip_allow_coordinator_parameter_tuning: {
    zh:
      '确认要允许吗？合作伙伴可在不改变算法和数据的情况下，自行发起调参任务，不需要获得您的授权。',
    en:
      'Are you sure you want to allow it? Partners can initiate adjustment tasks on their own without changing the algorithm and data, without your authorization.',
  },
  tip_model_evaluation: {
    zh: '可对单个模型进行评估',
    en: 'Evaluate single model',
  },
  tip_no_share_model_evaluation_report: {
    zh: '对方已选择不与您共享报告结果，如果相关诉求，请联系对方进行协商',
    en:
      'The other party has chosen not to share the results of the report with you. If you have relevant claims, please contact the other party for negotiation',
  },
  tip_no_tip_share_offline_prediction_result: {
    zh: '对方已选择不与您共享离线预测结果，如果相关诉求，请联系对方进行协商',
    en:
      'The other party has chosen not to share the offline prediction results with you. If you have a request, please contact the other party for negotiation',
  },
  tip_only_show_read_model: {
    zh: '仅展示所有参与方完成配置的模型',
    en: 'Only show models that have been configured by all participants',
  },
  tip_if_data_error_please_check_template: {
    zh: '如数据显示异常，请检查自定义模板是否符合编写规范',
    en:
      'If the data is abnormal, please check whether the custom template complies with the writing specifications',
  },
  tip_please_check_template: {
    zh: '请检查自定义模板是否符合编写规范',
    en: 'Please check whether the custom template complies with the writing specifications',
  },
  tip_model_compare_count_limit: {
    zh: '可对至少{{min}}个，至多{{max}}个评估对象进行对比',
    en: 'You can select at least {{min}} and at most {{max}} evaluation target for compare',
  },
  tip_confusion_matrix_normalization: {
    zh: '归一化后将展示样本被预测成各类别的百分比',
    en: 'After normalization, it will show the percentage of samples predicted into each category',
  },
  tip_training_metrics_visibility: {
    zh: '训练报告仅自己可见，如需共享报告，请前往训练详情页开启',
    en:
      'The training report is only visible to you. If you want to share the report, please go to the training details page',
  },
  tip_agree_authorization: {
    zh: '授权后，发起方可以运行模型训练并修改参与方的训练参数，训练指标将对所有参与方可见',
    en:
      'After agreeing to the authorization, the applicant can modify its own parameter configuration and resources on the opposite side and automatically run the model training, and the training indicators will be visible to all participants',
  },
  tip_learning_rate: {
    zh: '使用损失函数的梯度调整网络权重的超参数，​ 推荐区间（0.01-1]',
    en: 'The hyperparameter of the learning rate, recommended range (0.01-1]',
  },
  tip_max_iters: {
    zh: '该模型包含树的数量，推荐区间（5-20）',
    en: 'The number of trees in the model, recommended range (5-20)',
  },
  tip_max_depth: {
    zh: '树模型的最大深度，用来控制过拟合，推荐区间（4-7）',
    en: 'The maximum depth of the tree model, used to control overfitting, recommended range (4-7)',
  },
  tip_l2_regularization: {
    zh: '对节点预测值的惩罚系数，推荐区间（0.01-10）',
    en: 'The penalty coefficient of the prediction value of the node, recommended range (0.01-10)',
  },
  tip_max_bins: {
    zh: '离散化连续变量，可以减少数据稀疏度，一般不需要调整',
    en:
      'Discretization of continuous variables, can reduce the data sparsity, generally do not need to adjust',
  },
  tip_num_parallel: {
    zh: '建议与CPU核数接近',
    en: 'Recommended to be close to the number of CPU cores',
  },
  tip_epoch_num: {
    zh: '指一次完整模型训练需要多少次Epoch，一次Epoch是指将全部训练样本训练一遍',
    en:
      'The number of Epochs required for a complete model training, one Epoch is one time training all samples',
  },
  tip_verbosity: {
    zh: '有 0、1、2、3 四种等级，等级越大日志输出的信息越多',
    en:
      'There are four levels of verbosity, the level of which increases the amount of information output',
  },
  tip_image: {
    zh: '用于训练的镜像',
    en: 'Image used for training',
  },
  tip_file_ext: {
    zh: '目前支持.data, .csv or .tfrecord',
    en: 'Currently supports .data, .csv or .tfrecord',
  },
  tip_file_type: {
    zh: '目前支持csv or tfrecord',
    en: 'Currently supports csv or tfrecord',
  },
  tip_enable_packing: {
    zh: '提高计算效率，true 为优化，false 为不优化。',
    en: 'Increase the efficiency of computation, true is open, false is close.',
  },
  tip_ignore_fields: {
    zh: '不参与训练的字段',
    en: 'Fields not included in training',
  },
  tip_cat_fields: {
    zh: '类别变量字段，训练中会特别处理',
    en: 'Category fields, training will be specially processed',
  },
  tip_send_scores_to_follower: {
    zh: '是否将预测值发送至follower侧，fasle代表否，ture代表是',
    en: 'Whether to send the predicted value to the follower side, false is no, true is yes',
  },
  tip_send_metrics_to_follower: {
    zh: '是否将指标发送至follower侧，fasle代表否，ture代表是',
    en: 'Whether to send the indicators to the follower side, false is no, true is yes',
  },
  tip_verify_example_ids: {
    zh: '是否检验example_ids，一般情况下训练数据有example_ids，fasle代表否，ture代表是',
    en:
      'Whether to verify example_ids, generally training data has example_ids, false is no, true is yes',
  },
  tip_no_data: {
    zh: '针对标签方没有特征的预测场景，fasle代表有特征，ture代表无特征。',
    en:
      'For the scenario where the label does not have features, false is features, true is no features.',
  },
  tip_label_field: {
    zh: '用于指定label',
    en: 'Label field',
  },
  tip_load_model_name: {
    zh: '评估和预测时，根据用户选择的模型，确定该字段的值。',
    en:
      'When evaluating and predicting, determine the value of this field according to the user selection of the model.',
  },
  tip_shuffle_data_block: {
    zh: '打乱数据顺序，增加随机性，提高模型泛化能力',
    en: 'Shuffle the data order, increase the randomness, improve the model generality',
  },
  tip_save_checkpoint_secs: {
    zh: '模型多少秒保存一次',
    en: 'The model is saved every n seconds',
  },
  tip_save_checkpoint_steps: {
    zh: '模型多少step保存一次',
    en: 'The model is saved every n steps',
  },
  tip_load_checkpoint_filename: {
    zh: '加载文件名，用于评估和预测时选择模型',
    en: 'Load file name, used to select the model when evaluating and predicting',
  },
  tip_load_checkpoint_filename_with_path: {
    zh: '加载文件路径，用于更细粒度的控制到底选择哪个时间点的模型',
    en: 'Load file path, used to control the selection of the model at a fine-grained level',
  },
  tip_sparse_estimator: {
    zh: '是否使用火山引擎的SparseEstimator，由火山引擎侧工程师判定，客户侧默认都为false',
    en:
      'Whether to use the SparseEstimator of the engine, determined by the engine side engineer, the default is false',
  },
  tip_steps_per_sync: {
    zh: '用于指定参数同步的频率，比如step间隔为10，也就是训练10个batch同步一次参数。',
    en: 'Frequency at which parameters are synchronized, for example, 10 steps per batch',
  },
  tip_feature_importance: {
    zh: '数值越高，表示该特征对模型的影响越大',
    en: 'The higher the value, the greater the influence of this feature on the model',
  },
  tip_metric_is_publish: {
    zh: '开启后，将与合作伙伴共享本次训练指标',
    en: 'After opening, the training indicators will be shared with participant',
  },

  state_success: { zh: '成功', en: 'Success' },
  state_failed: { zh: '失败', en: 'Fail' },
  state_ready_to_run: { zh: '待运行', en: 'Ready to run' },
  state_paused: { zh: '暂停', en: 'Pause' },
  state_running: { zh: '运行中', en: 'Running' },
  state_invalid: { zh: '已禁用', en: 'Invalid' },
  state_unknown: { zh: '状态未知', en: 'Unknown' },

  label_model_type_unspecified: { zh: '模型集', en: 'Unspecified' },
  label_model_type_tree: { zh: '树模型', en: 'Tree model' },
  label_model_type_nn: { zh: 'NN模型', en: 'NN model' },
  label_model_source_from_model_job: {
    zh: '{{modelJobName}}训练任务',
    en: 'train job {{modelJobName}}',
  },
  label_model_source_from_workflow: {
    zh: '{{workflowName}}工作流-{{jobName}}任务',
    en: '{{workflowName}} workflow-{{jobName}} job',
  },
  label_enable_schedule_train: { zh: '启用定时重训', en: 'Enable schedule train' },
  label_metric_is_publish: { zh: '共享训练报告', en: 'Share the training report' },

  name_model: { zh: '模型', en: 'model' },
  name_model_set: { zh: '模型集', en: 'model set' },
  name_algorithm: { zh: '算法', en: 'algorithm' },
  name_evaluation_job: { zh: '评估任务', en: 'evaluation job' },
  name_prediction_job: { zh: '预测任务', en: 'prediction job' },
  name_compare_report: { zh: '对比报告', en: 'compare report' },

  form_field_name: {
    zh: '名称',
    en: 'name',
  },
  form_field_name_placeholder: {
    zh: '请输入名称',
    en: 'Please enter the name of the evaluation',
  },
  form_field_comment: {
    zh: '描述',
    en: 'description',
  },
  form_field_comment_placeholder: {
    zh: '最多为 200 个字符',
    en: 'Up to 200 characters',
  },
  form_field_job_type: {
    zh: '联邦配置',
    en: 'Federal type',
  },
  form_field_model_id: {
    zh: '模型',
    en: 'model',
  },
  form_field_dataset: {
    zh: '数据集',
    en: 'dataset',
  },
  form_field_config: {
    zh: '资源模板',
    en: 'resource template',
  },
  form_section_evaluation_config: {
    zh: '评估配置',
    en: 'Evaluation configuration',
  },
  form_section_prediction_config: {
    zh: '预测配置',
    en: 'Prediction configuration',
  },
  form_section_resource: {
    zh: '资源配置',
    en: 'Resource configuration',
  },
  form_btn_submit: {
    zh: '提交并发送',
    en: 'Submit and send',
  },
  form_section_resource_tip: {
    zh: 'NN模型的资源配置',
    en: 'Resource configuration of NN model',
  },
  form_schedule_train_tip: {
    zh: '启用该功能将间隔性地重跑训练任务，且每次训练都将从最新的可用版本开始',
    en:
      'Enabling this feature reruns training tasks at intervals, with each session starting with the latest available version',
  },
};

export default separateLng(modelCenter);
