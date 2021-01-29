import { separateLng } from 'i18n/helpers';

const error = {
  status: { zh: '状态' },
  no_result: { zh: '暂无数据集' },
  selected_items: { zh: '已选择 {{count}} 项' },

  btn_create: { zh: '创建数据集', en: 'Create Dataset' },
  btn_add_batch: { zh: '追加数据', en: ' Add databatch' },
  btn_view_records: { zh: '查看记录', en: 'View records' },
  btn_finish_n_import: { zh: '完成创建并导入', en: 'Submit and start importing' },
  btn_import: { zh: '开始导入', en: 'Start importing' },

  col_name: { zh: '数据集名称' },
  col_type: { zh: '类型' },
  col_files_size: { zh: '数据总大小' },
  col_creator: { zh: '创建者' },

  msg_start_importing: { zh: '数据集创建成功，数据文件开始导入' },
  msg_name_required: { zh: '数据集名称为必填项' },
  msg_type_required: { zh: '请选择数据集类型' },
  msg_event_time_required: { zh: '请选择数据产生时间' },
  msg_quit_warning: { zh: '取消后，已配置内容将不再保留' },
  msg_file_required: { zh: '请选择需要导入的文件' },
  msg_id_required: { zh: '缺少数据集 ID，请检查' },
  msg_is_importing: { zh: '存在数据正在导入中，暂不支持追加数据' },

  tip_move_file: { zh: '导入成功后将移除所有原文件以节省磁盘空间' },

  label_name: { zh: '数据集名称' },
  label_type: { zh: '数据集类型' },
  label_comment: { zh: '数据集说明' },
  label_event_time: { zh: '数据产生时间' },
  label_move_file: { zh: '导入后移除源文件' },

  placeholder_name_searchbox: { zh: '输入数据名称搜索', en: 'Search by name' },
  placeholder_name: { zh: '请输入数据集名称' },
  placeholder_comment: { zh: '请输入数据集说明' },
  placeholder_filename_filter: { zh: '输入文件名进行筛选' },

  title_create: { zh: '创建数据集' },

  state_importing: { zh: '导入中（{{imported}}/{{total}}）' },
  state_available: { zh: '可用' },
  state_error: { zh: '导入失败' },
  state_unknown: { zh: '状态未知' },

  step_basic: { zh: '基础配置' },
  step_add_batch: { zh: '选择数据文件' },
};

export default separateLng(error);
