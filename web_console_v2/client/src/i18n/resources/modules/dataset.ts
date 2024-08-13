import { separateLng } from 'i18n/helpers';

const datasets = {
  status: { zh: '状态' },
  no_result: { zh: '暂无数据集' },
  selected_items: { zh: '已选择 {{count}} 项' },

  btn_create: { zh: '创建数据集', en: 'Create Dataset' },
  btn_create_dataset_job: { zh: '创建数据任务', en: 'Create Dataset job' },
  btn_add_batch: { zh: '追加数据', en: ' Add databatch' },
  btn_view_records: { zh: '查看记录', en: 'View records' },
  btn_finish_n_import: { zh: '完成创建并导入', en: 'Submit and start importing' },
  btn_import: { zh: '开始导入', en: 'Start importing' },
  btn_create_now: { zh: '确认创建', en: 'Create' },
  btn_copy_path: { zh: '复制路径', en: 'Copy path' },
  btn_data_join: { zh: '数据求交', en: 'Data join' },
  btn_more_action: { zh: '...', en: '...' },
  btn_create_join_job: { zh: '创建求交任务', en: 'Start join job' },
  btn_export_dataset: { zh: '导出', en: 'Export' },
  btn_export_dataset_go_back: { zh: '前往求交数据集列表', en: 'Go back' },
  btn_publish_project: { zh: '发布', en: 'Publish' },
  btn_unpublish_project: { zh: '撤销发布', en: 'Unpublish' },
  btn_create_data_source: { zh: '添加数据源', en: 'Create data source' },
  btn_job_stop: { zh: '停止运行', en: 'Stop Running' },

  col_id: { zh: 'ID' },
  col_path: { zh: '文件路径' },
  col_name: { zh: '名称' },
  col_file_name: { zh: '数据源地址文件' },
  col_type: { zh: '类型' },
  col_files_size: { zh: '数据大小' },
  col_creator: { zh: '创建者' },
  col_modification_time: { zh: '最近修改时间' },
  col_project: { zh: '关联工作区' },
  col_num_example: { zh: '数据集样本量' },
  col_participant: { zh: '合作伙伴名称' },
  col_data_format: { zh: '数据格式' },
  col_updated_at: { zh: '最近更新' },
  col_data_source_url: { zh: '数据来源', en: 'data source url' },
  col_dataset_path: { zh: '数据集路径', en: 'Dataset path' },
  col_publish_state: { zh: '发布状态', en: 'Publish state' },
  col_dataset_state: { zh: '数据集状态', en: 'Dataset state' },
  col_participant_name: { zh: '参与方', en: 'Participant' },
  col_data_value: { zh: '数据价值', en: 'Data value' },
  col_use_unit_price: { zh: '使用单价', en: 'Unit price' },

  // for dataset task job table col
  col_job_name: { zh: '任务名称', en: 'Task name' },
  col_job_type: { zh: '任务类型', en: 'Task type' },
  col_job_status: { zh: '任务状态', en: 'Task status' },
  col_job_coordinator: { zh: '任务发起方', en: 'Task coordinator' },
  col_job_create_time: { zh: '创建时间', en: 'Create time' },
  col_job_start_time: { zh: '开始时间', en: 'Start time' },
  col_job_finish_time: { zh: '结束时间', en: 'Finish time' },
  col_job_running_time: { zh: '运行时长', en: 'Running Time' },
  col_job_operation: { zh: '操作', en: 'Operation' },

  col_ledger_hash: { zh: '哈希', en: 'Hash' },
  col_ledger_block: { zh: '所属块', en: 'Block' },
  col_ledger_trade_block_id: { zh: '交易块内ID', en: 'Trade block ID' },
  col_ledger_chain_time: { zh: '上链时间', en: 'Time of chain' },
  col_ledger_sender: { zh: '发送方', en: 'Sender' },
  col_ledger_receiver: { zh: '接收方', en: 'Receiver' },
  col_ledger_trade_fee: { zh: '交易费用', en: 'Fee of trade' },
  col_ledger_trade_status: { zh: '交易状态', en: 'Status of trade' },
  col_ledger_trade_info: { zh: '交易信息', en: 'Information of trade' },

  msg_start_importing: { zh: '数据集创建成功，数据文件开始导入' },
  msg_name_required: { zh: '数据集名称为必填项' },
  msg_type_required: { zh: '请选择数据集类型' },
  msg_event_time_required: { zh: '请选择数据产生时间' },
  msg_quit_warning: { zh: '取消后，已配置内容将不再保留' },
  msg_file_required: { zh: '请选择需要导入的文件' },
  msg_id_required: { zh: '缺少数据集 ID，请检查' },
  msg_is_importing: { zh: '存在数据正在导入中，暂不支持追加数据' },
  msg_todo_tasks: { zh: '{{count}}条待处理任务' },
  msg_edit_ok: { zh: '数据集编辑成功' },
  msg_export_id_empty: {
    zh: '导出任务ID缺失，请手动跳转「任务管理」查看详情',
    en: 'The ID of the export task is missing. Go to Task Management to view details',
  },

  tip_move_file: { zh: '导入成功后将移除所有原文件以节省磁盘空间' },
  tip_type_struct: { zh: '支持.csv/.tfrecords格式' },
  tip_type_picture: { zh: '支持.jpeg/.png/.bmp/.gif格式' },
  tip_limit_count: { zh: '仅展示最近{{count}}条', en: 'Show only the last {{count}} tasks' },
  tip_files_size: {
    zh: '数据以系统格式存储的大小，较源文件会有一定变化',
    en: 'The size of the data stored in the system format will vary from the source file',
  },

  label_name: { zh: '数据集名称' },
  label_type: { zh: '数据集类型' },
  label_data_type: { zh: '数据类型' },
  label_join_type: { zh: '求交类型' },
  label_source_location: { zh: '数据源地址' },
  label_data_source: { zh: '数据源', en: 'Data source' },
  label_data_job_type: { zh: '数据任务', en: 'Data job type' },
  label_data_job_type_create: { zh: '求交', en: 'Join' },
  label_data_job_type_alignment: { zh: '对齐', en: 'Alignment' },
  label_data_job_type_light_client_join: { zh: '轻客户端求交', en: 'Light client join' },
  label_data_job_type_import: { zh: '导入', en: 'import' },
  label_data_job_type_export: { zh: '导出', en: 'export' },
  label_data_join_type: { zh: '求交方式', en: 'Data join type' },
  label_data_join_type_normal: { zh: '数据求交', en: 'Data join' },
  label_data_join_type_psi: { zh: 'RSA-PSI 求交', en: 'RSA-PSI Data join' },
  label_data_join_type_light_client: { zh: 'RSA-PSI 求交', en: 'RSA-PSI Data join' },
  label_data_join_type_ot_psi_data_join: { zh: 'OT-PSI 求交', en: 'OT-PSI Data join' },
  label_dataset_my: { zh: '我方数据集', en: 'My dataset' },
  label_dataset_participant: { zh: '合作伙伴数据集', en: 'Participant dataset' },
  label_params_my: { zh: '我方参数', en: 'My params' },
  label_params_participant: { zh: '合作伙伴参数', en: 'Participant params' },
  label_comment: { zh: '数据集描述' },
  label_event_time: { zh: '数据产生时间' },
  label_move_file: { zh: '导入后移除源文件' },
  label_import_by: { zh: ' 导入方式' },
  label_import_by_remote: { zh: '数据源导入' },
  label_import_by_local: { zh: '本地导入' },
  label_raw_dataset: { zh: '原始数据集' },
  label_intersection_dataset: { zh: '求交数据集' },
  label_struct_type: { zh: '结构化数据' },
  label_picture_type: { zh: '图片' },
  label_feature_amount: { zh: '特征量' },
  label_row_amount: { zh: '数据集样本量' },
  label_type_amount: { zh: '分类数' },
  label_picture_amount: { zh: '总图片量' },
  label_total_cols: { zh: '总列数', en: 'Total cols' },
  label_total_rows: { zh: '总行数', en: 'Total rows' },
  label_update_time: { zh: '更新时间', en: 'Update time' },
  label_intersection_rate: { zh: '求交率', en: 'Intersection rate' },
  label_amount_of_data: { zh: '我方数据量', en: 'Number of our data' },
  label_amount_of_intersection: { zh: '交集数', en: 'Number of intersection' },
  label_my_dataset: { zh: '我方数据集', en: 'Processed datasets' },
  label_participant_dataset: { zh: '合作伙伴数据集', en: 'Participant datasets' },
  label_participant_dataset_revoke: {
    zh: '对方已撤销发布',
    en: 'The participant has withdrawn the release',
  },

  label_rsa_psi_data_join: { zh: 'RSA-PSI 求交', en: 'RSA PSI data join' },
  label_light_client_rsa_psi_data_join: {
    zh: 'LIGHT_CLIENT_RSA_PSI数据求交',
    en: 'Light client RSA PSI data join',
  },
  label_ot_psi_data_join: { zh: 'OT-PSI数据求交', en: 'OT PSI data join' },
  label_data_join: { zh: '数据求交', en: 'Data join' },
  label_data_alignment: { zh: '数据对齐', en: 'Data alignment' },
  label_import_source: { zh: '数据导入', en: 'Import source' },

  label_blockchain_storage: { zh: '区块链存证', en: 'Blockchain storage' },
  label_all_records: { zh: '追加记录' },
  label_schema: { zh: '校验错误信息' },
  label_join_workflows: { zh: '求交任务' },
  label_data_preview: { zh: '数据探查', en: 'Data preview' },
  label_image_preview: { zh: '图片预览', en: 'Image preview' },
  label_data_job_detail: { zh: '任务详情', en: 'Processed datasets' },
  label_processed_dataset: { zh: '结果数据集', en: 'Processed datasets' },
  label_relative_dataset: { zh: '下游数据集', en: 'Relative datasets' },
  label_need_schema_check: { zh: '数据检验', en: 'Data validation' },
  label_json_schema: { zh: '校验规则', en: 'Validation rule' },
  label_todo_tasks: { zh: '待处理任务', en: 'Todo tasks' },
  label_start_task: { zh: '发起了任务', en: 'start task' },
  label_export_path: { zh: '导出路径', en: 'Export path' },
  label_coordinator_self: { zh: '本方', en: 'this party' },
  label_local_upload: { zh: '本地上传', en: 'Local upload' },
  label_local_export: { zh: '导出地址', en: 'Export Url' },
  label_light_client: { zh: '轻量', en: 'Light client' },
  label_upload_by_light_client: { zh: '由客户侧本地上传', en: 'upload locally by light client' },
  label_data_source_name: { zh: '数据源名称', en: 'Data source name' },
  label_data_source_url: { zh: '数据来源', en: 'Data source url' },
  label_file_name_preview: { zh: '文件名预览', en: 'File name preview' },
  label_upload_by_data_source: { zh: '数据源上传', en: 'Upload from dataSource' },
  label_upload_task: { zh: '导入任务', en: 'Import Task' },
  label_data_not_found: { zh: '数据集信息未找到', en: 'Dataset Info Not Found' },

  label_check_running_status_job: { zh: '查看运行中任务', en: 'Check the running jobs' },
  label_job_list: { zh: '任务管理', en: 'Job manager' },
  label_publish_to_workspace: { zh: '发布至工作区', en: 'Publish to workspace' },
  label_publish_credits: { zh: '积分', en: 'Credits' },
  label_use_price: { zh: '使用单价', en: 'Unit price' },
  label_job_wait_to_run: { zh: '待运行', en: 'Waiting to run' },
  label_current_dataset_value: { zh: '当前数据价值', en: 'Value of the dataset' },

  label_resource_allocation: { zh: '资源配置', en: 'Resource allocation' },
  label_input_params: { zh: '输入参数', en: 'Input params' },
  label_job_config: { zh: '任务配置', en: 'Job config' },
  label_dataset_empty: { zh: '空集', en: 'Empty Dataset' },

  label_dataset_check: { zh: '数据校验', en: 'Data Check' },
  label_dataset_join_checker: { zh: '求交数据校验', en: 'Join Data Checker' },
  label_dataset_numeric_checker: { zh: '全数值特征校验', en: 'Numeric Checker' },

  placeholder_name_searchbox: { zh: '输入数据集名称搜索', en: 'Search by name' },
  placeholder_searchbox_data_source: { zh: '输入数据源名称', en: 'Search by data source name' },
  placeholder_name: { zh: '请输入数据集名称' },
  placeholder_comment: {
    zh: '最多为 200 个字符',
    en: 'Up to 200 characters',
  },
  placeholder_event_time: { zh: '请选择时间' },
  placeholder_filename_filter: { zh: '输入文件名进行筛选' },
  placeholder_directory_filter: { zh: '切换其他文件夹(按回车确认)' },
  placeholder_datasource_url: {
    zh: '请填写有效文件目录地址，非文件，如 hdfs:///home/folder',
    en: 'Please fill in a valid file directory address, not a file, such as hdfs:///home/folder',
  },
  placeholder_job_name: { zh: '输入任务名称', en: 'Input the name of task' },

  title_create: { zh: '创建数据集', en: 'Create dataset' },
  title_edit: { zh: '编辑数据集' },
  title_export_dataset: { zh: '导出数据集', en: 'Export dataset' },
  title_export_start_time: {
    zh: '开始时间: {{time}}',
    en: 'Start time: {{time}}',
  },
  tile_export_end_time: {
    zh: '结束时间: {{time}}',
    en: 'End time: {{time}}',
  },
  title_export_path: { zh: '导出路径: {{path}}', en: 'Export path: {{path}}' },
  title_create_data_source: { zh: '创建数据源', en: 'Dreate data source' },
  title_edit_data_source: { zh: '编辑数据源', en: 'Edit data source' },
  title_base_config: { zh: '基本配置', en: 'Base config' },
  title_data_source_import: { zh: '数据源导入', en: 'Data source import' },
  title_local_import: { zh: '本地导入', en: 'Local import' },

  title_task_flow: { zh: '任务流程', en: 'Task flow' },
  title_error_message: { zh: '错误信息', en: 'Error message' },

  state_importing: { zh: '导入中' },
  state_available: { zh: '可用' },
  state_import_error: { zh: '导入失败' },
  state_unknown: { zh: '状态未知', en: 'Unknown' },
  state_processing: { zh: '处理中' },
  state_process_failed: { zh: '处理失败' },
  state_deleting: { zh: '删除中' },
  state_error: { zh: '异常' },
  state_checking: { zh: '校验中' },
  state_checked: { zh: '校验通过' },
  state_check_error: { zh: '校验不通过' },
  state_exporting: { zh: '导出中', en: 'Exporting' },
  state_export_success: { zh: '导出成功', en: 'Export success' },
  state_export_failed: { zh: '导出失败', en: 'Export failed' },
  state_stopped: { zh: '已停止', en: 'stopped' },

  state_dataset_job_pending: { zh: '待运行', en: 'Pending' },
  state_dataset_job_running: { zh: '运行中', en: 'Running' },
  state_dataset_job_succeeded: { zh: '成功', en: 'Succeeded' },
  state_dataset_job_failed: { zh: '失败', en: 'Failed' },
  state_dataset_job_stopped: { zh: '已停止', en: 'stopped' },

  state_text_published: { zh: '已发布', en: 'Published' },
  state_text_unpublished: { zh: '未发布', en: 'Unpublished' },
  state_text_published_with_project: { zh: '已发布至工作区', en: 'Published' },
  state_text_unpublished_with_project: { zh: '未发布至工作区', en: 'Unpublished' },

  state_transaction_failed: { zh: '失败', en: 'Failed' },
  state_transaction_success: { zh: '成功', en: 'Succeeded' },
  state_transaction_processing: { zh: '处理中', en: 'Processing' },

  step_basic: { zh: '基础配置' },
  step_add_batch: { zh: '选择数据文件' },

  tip_only_show_read_task: {
    zh: '仅展示所有参与方完成配置的任务',
    en: 'Only show that all participants have completed the configured tasks',
  },
  tip_state_process: {
    zh: '数据处理中，请稍后',
    en: 'Data processing, please wait',
  },
  tip_state_error: {
    zh: '抱歉，数据暂时无法显示',
    en: 'Sorry, the data is temporarily unavailable',
  },
  tip_check_error: { zh: '请进入数据集详情，查看校验错误信息' },
  tip_file_not_found: { zh: '输入路径不存在！', en: 'The input path does not exist!' },
  tip_file_no_permission: { zh: '无权限访问该路径！', en: 'No permission to access the path！' },
  tip_json_schema: {
    zh: '支持以Json Schema的方式输入，只校验规则中的字段，其他字段不校验',
    en:
      'Support input in Json Schema format, only the fields in the rule will be verified, other fields will be ignored',
  },
  tip_data_source: {
    zh: '数据源指数据的来源，创建数据源即定义访问数据存储空间的地址',
    en:
      'The data source refers to the source of the data. Creating a data source defines the address for accessing the data storage space.',
  },
  tips_publish: {
    zh: '发布后，工作区中合作伙伴可使用该数据集',
    en: 'Once published, the data set is available to partners in the workspace',
  },
  tips_publish_default_value: { zh: '100积分', en: '100 points' },
  tips_first_publish: { zh: '首次发布可得 100 积分', en: '100 credits for first publish' },
  tips_relative_dataset: {
    zh: '通过使用本数据集所产生的数据集',
    en: 'The data set generated by using this data set',
  },

  tips_data_checker_join: {
    zh: '当数据集需用于求交时，需勾选该选项，将要求数据集必须有raw_id 列且没有重复值',
    en:
      'Select this option when the data set is used for intersection. The data set must have raw ID columns with no duplicate values',
  },
  tips_data_checker_numeric: {
    zh: '当数据集需用于树模型训练时，需勾选该选项，将要求数据集特征必须为全数值',
    en:
      'Select this option when the data set is used for tree model training. The data set features must be full values',
  },

  msg_title_confirm_delete: { zh: '确认删除数据集？', en: 'Confirm to delete the dataset?' },
  msg_content_confirm_delete: {
    zh: '删除操作无法恢复，请谨慎操作',
    en: 'After deleting, the data set will be inoperable, please delete it carefully',
  },
  msg_export_success: {
    zh: '导出成功',
    en: 'Export success',
  },
  msg_export_failed: {
    zh: '导出失败',
    en: 'Export failed',
  },
  msg_publish_confirm: {
    zh: '发布「{{name}}」至工作区？',
    en: 'Publish "{{name}}" to the workspace?',
  },
  msg_publish_tip: {
    zh: '发布后，在工作区中可使用该数据集',
    en: 'After publishing, the data set can be used in the workspace',
  },
  msg_unpublish_confirm: {
    zh: '确认要撤销发布「{{name}}」？',
    en: 'Confirm to unpublish "{{name}}"?',
  },
  msg_unpublish_tip: {
    zh: '撤销后，工作区的合作伙伴将不能使用该数据集',
    en: 'After unpublishing, the partner in the workspace will not be able to use the dataset',
  },

  msg_title_confirm_delete_data_source: {
    zh: '确认要删除「{{name}}」？',
    en: 'Are you sure you want to delete "{{name}}"?',
  },
  msg_content_confirm_delete_data_source: {
    zh: '删除后，当该数据源将无法恢复，请谨慎操作。',
    en: 'After deletion, when the data source cannot be recovered, please operate with caution.',
  },

  msg_connecting: {
    zh: '连接中',
    en: 'connecting',
  },
  msg_connection_success: {
    zh: '连接成功',
    en: 'connection success',
  },
  msg_connection_fail: {
    zh: '连接失败',
    en: 'connection fail',
  },

  msg_no_support_data_job: {
    zh: '暂不支持该类型的数据任务',
    en: 'This data job is not currently supported',
  },

  msg_title_confirm_stop_job: {
    zh: '确认要停止「{{name}}」？',
    en: 'Are you sure you want to stop "{{name}}"?',
  },

  msg_content_confirm_stop_job: {
    zh: '停止后，该任务不能再重新运行，请谨慎操作',
    en: 'After stopped, the job cannot be restart, please operate with caution',
  },

  msg_title_confirm_delete_job: {
    zh: '确认要删除「{{name}}」？',
    en: 'Are you sure you want to delete "{{name}}"?',
  },

  msg_content_confirm_delete_job: {
    zh: '删除后，该任务及信息将无法恢复，请谨慎操作',
    en:
      'After deletion, the job and related info cannot be recovered, please operate with caution.',
  },

  msg_stop_failed: {
    zh: '停止失败',
    en: 'Stop Failed',
  },

  msg_delete_failed: {
    zh: '删除失败',
    en: 'Delete Failed',
  },

  msg_create_success: {
    zh: '创建成功，数据集可用后将自动发布',
    en:
      'The data set has been created successfully and will be published automatically when it is available',
  },

  tag_raw: { zh: '原始', en: 'Raw' },
  tag_processed: { zh: '结果', en: 'Processed' },
};

export default separateLng(datasets);
