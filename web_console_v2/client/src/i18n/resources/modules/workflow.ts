import { I18nMessageModule, separateLng } from 'i18n/helpers';

const workflow: I18nMessageModule = {
  no_result: { zh: '暂无工作流' },
  no_tpl: { zh: '暂无工作流模板' },
  execution_detail: { zh: '工作流详情' },
  name: { zh: '工作流名称' },
  our_config: { zh: '我方配置' },
  peer_config: { zh: '对方配置' },
  federated_note: { zh: '与对方工作流相同颜色的模块为关联模块' },
  ptcpt_permission: { zh: '合作伙伴编辑权限' },
  current_config: { zh: '当前配置' },
  create_workflow: { zh: '创建工作流', en: 'Create workflow' },
  edit_workflow: { zh: '编辑工作流', en: 'Edit workflow' },
  create_tpl: { zh: '新建模板', en: 'Create template' },
  edit_tpl: { zh: '编辑模板', en: 'Edit template' },
  fork_workflow: { zh: '复制工作流', en: 'Fork workflow' },
  forked_from: { zh: '复制于', en: 'Forked from' },

  action_re_run: { zh: '重新运行' },
  action_run: { zh: '立即运行' },
  action_configure: { zh: '立即配置' },
  action_stop_running: { zh: '停止运行' },
  action_fork: { zh: '复制' },
  action_detail: { zh: '详情' },
  action_show_report: { zh: '查看模型报告' },
  action_download: { zh: '下载' },
  action_invalid: { zh: '禁用' },
  action_edit: { zh: '编辑' },

  btn_inspect_logs: { zh: '查看日志' },
  btn_close: { zh: '关闭' },
  btn_conf_done: { zh: '配置完成' },
  btn_conf_next_step: { zh: '配置下一步（{{current}}/{{total}}）' },
  btn_see_peer_config: { zh: '查看对方配置' },
  btn_hide_peer_config: { zh: '隐藏对方配置' },
  btn_send_2_ptcpt: { zh: '发送给合作伙伴' },
  btn_submit_edit: { zh: '提交更改' },
  btn_auto_refresh_logs: { zh: '自动刷新日志' },
  btn_pause_auto_refresh: { zh: '停止自动刷新' },
  btn_full_screen: { zh: '全屏查看日志' },
  btn_has_new_logs: { zh: '有新的日志' },
  btn_fetch_metrics: { zh: '点击加载数据' },
  btn_retry: { zh: '重试' },
  btn_access_ctrl: { zh: '权限配置面板' },
  btn_add_var: { zh: '新增自定义变量' },
  btn_upload_tpl: { zh: '上传模板' },
  btn_go_create_new_tpl: { zh: '没有想要的模板？点击创建新模版' },
  btn_preview_kibana: { zh: '预览' },
  btn_preview_kibana_fullscreen: { zh: '在新窗口预览' },
  btn_add_kibana_chart: { zh: '添加新的图表' },

  col_status: { zh: '任务状态' },
  col_project: { zh: ' 隶属项目' },
  col_creator: { zh: ' 创建者' },
  col_date: { zh: ' 创建时间' },
  col_actions: { zh: '操作' },
  col_pod: { zh: 'POD' },
  col_worker_status: { zh: '运行状态' },
  col_worker_type: { zh: '类型' },
  col_tpl_name: { zh: '模版名' },
  col_group_alias: { zh: 'Group 别名' },
  col_pod_name: { zh: 'Pod' },
  col_pod_ip: { zh: 'IP' },

  state_success: { zh: '成功' },
  state_failed: { zh: '失败' },
  state_stopped: { zh: '已停止' },
  state_running: { zh: '运行中' },
  state_prepare_run: { zh: '正在启动中' },
  state_prepare_stop: { zh: '正在停止中' },
  state_warmup_underhood: { zh: '系统预热中' },
  state_pending_accept: { zh: '待配置' },
  state_ready_to_run: { zh: '配置成功' },
  state_configuring: { zh: '合作伙伴配置中' },
  state_invalid: { zh: '已禁用' },
  state_unknown: { zh: '状态未知' },

  sent_failed: { zh: '发送失败' },
  sent_failed_desc: {
    zh: '与合作伙伴连接失败，失败原因，请检查连接状态成功后在工作流列表中重新发送',
  },
  override_warn: { zh: '重新运行将覆盖历史结果' },
  override_warn_desc: { zh: '是否确认重新运行当前工作流任务将覆盖历史运行结果？' },

  label_name: { zh: '工作流名称' },
  label_group_alias: { zh: 'Group' },
  label_enable_batch_update_interval: { zh: '启用定时重训' },
  label_batch_update_interval: { zh: '重训间隔' },
  label_global_config: { zh: '全局配置' },
  label_project: { zh: '关联项目' },
  label_peer_forkable: { zh: '合作伙伴复制权限' },
  label_template: { zh: '工作流模板' },
  label_allow: { zh: '允许' },
  label_not_allow: { zh: '不允许' },
  label_exist_template: { zh: '选择已有' },
  label_pairing_exist_template: { zh: '选择配对模板' },
  label_new_template: { zh: '新建模板' },
  label_pairing_new_template: { zh: '上传配对模板' },
  label_new_template_name: { zh: '模板名称' },
  label_is_left: { zh: 'is Left' },
  label_upload_template: { zh: '上传模板文件' },
  label_template_comment: { zh: '工作流模板说明' },
  label_template_name: { zh: '模板 (Group)' },
  label_running_time: { zh: '运行时长' },
  label_role: { zh: 'Role' },
  label_job_created: { zh: '任务创建时间' },
  label_job_vars: { zh: '任务参数' },
  label_job_metrics: { zh: '任务运行结果指标' },
  label_job_logs: { zh: '任务运行日志' },
  label_pod_list: { zh: '各 worker 运行日志及状态' },
  label_job_reuseable: { zh: '继承结果' },
  label_job_nonreusable: { zh: '重新运行' },
  label_job_name: { zh: 'Job 名称' },
  label_job_type: { zh: '任务类型' },
  label_job_federated: { zh: '是否联邦' },
  label_job_yaml: { zh: 'YAML 模板' },
  label_var_name: { zh: 'Key' },
  label_peer_access: { zh: '对侧权限' },
  label_default_val: { zh: '默认值' },
  label_var_comp: { zh: '请选择组件' },
  label_var_enum: { zh: '可选项' },
  label_forkable: { zh: '是否可复制' },
  label_metric_public: { zh: '公开Metric' },
  label_use_original_tpl: { zh: '保持原先模板' },
  label_choose_new_tpl: { zh: '选择其他模板' },
  label_job_basics: { zh: '任务基础信息' },
  label_job_kibana_metrics: { zh: 'Kibana 参数' },

  placeholder_name_searchbox: { zh: '根据工作流名称搜索' },
  placeholder_uuid_searchbox: { zh: '根据 UUID 搜索' },
  placeholder_name: { zh: '请输入工作流名称' },
  placeholder_template: { zh: '请选择模板' },
  placeholder_project: { zh: '请关联一个项目' },
  placeholder_comment: { zh: '请输入工作流模板说明' },
  placeholder_template_name: { zh: '请输入模板名称' },
  placeholder_fetch_metrics: { zh: '查询 Metrics 性能消耗较大，故需手动确认执行' },
  placeholder_no_metrics: { zh: '当前未查询到相关指标' },
  placeholder_jobname: { zh: '请输入 Job 名' },
  placeholder_job_type: { zh: '请选择任务类型' },
  placeholder_var_name: { zh: '请输入变量名 （仅允许英语及下划线' },
  placeholder_default_val: { zh: '按需设置变量默认值' },
  placeholder_dataset: { zh: '请选择数据集' },
  placeholder_metric_not_public: { zh: '对侧未公开指标可见性，如需查看请联系对侧' },
  placeholder_aggregator: { zh: '指定 Aggregator' },
  placeholder_interval: { zh: 'Interval' },
  placeholder_x_asix: { zh: '例: tag.event_time' },
  placeholder_start_time: { zh: '开始时间' },
  placeholder_end_time: { zh: '结束时间' },
  placeholder_timers: { zh: 'Timers' },
  placeholder_json_syntax: { zh: '' },
  placeholder_fill_kibana_form: {
    zh:
      '右侧确认筛选项后查看指标，Kibana加载时间可能稍长甚至出现长时间空白，属于正常现象，请耐心等待',
  },
  placeholder_kibana_timer: {
    zh: '输入多个 timer 名称',
  },

  msg_sent_success: { zh: '工作流发送成功' },
  msg_template_required: { zh: '请选择一个模板！' },
  msg_min_10_interval: { zh: ' 最小间隔为 10 分钟' },
  msg_get_template_failed: { zh: '获取模板列表失败' },
  msg_only_1_tpl: { zh: '只允许上传一个模板文件！' },
  msg_config_unfinished: { zh: '未完成配置，请先完成配置后再次点击发送' },
  msg_config_unconfirm_or_unfinished: { zh: '双侧配置未确认或未完成，请检查后进行发送' },
  msg_sure_2_cancel_create: { zh: '确认取消创建工作流？' },
  msg_sure_2_cancel_edit: { zh: '确认取消编辑工作流？' },
  msg_sure_2_cancel_fork: { zh: '确认取消复制工作流？' },
  msg_sure_2_cancel_tpl: { zh: '确认取消编辑模板吗？' },
  msg_sure_2_exist_create: { zh: '确定要离开吗，当前表单内容将全部丢失！' },
  msg_sure_2_exist_edit: { zh: '确定要离开吗，当前表单内容将全部丢失！' },
  msg_will_drop_tpl_config: { zh: '取消后，已配置的模板内容将不再保留' },
  msg_effect_of_cancel_create: { zh: '取消后，已配置内容将不再保留' },
  msg_project_required: { zh: '请选择项目！' },
  msg_name_required: { zh: '请输入名称！' },
  msg_no_abailable_tpl: { zh: '暂无可用模板，请手动新建' },
  msg_pairing_no_abailable_tpl: { zh: '暂无可用的配对模板，请手动上传' },
  msg_tpl_file_required: { zh: '请选择一个合适的模板文件！' },
  msg_tpl_name_required: { zh: '请输入模板名！' },
  msg_tpl_config_missing: { zh: '模板格式错误，缺少 config 字段！' },
  msg_tpl_alias_missing: { zh: '模板格式错误，缺少 config.group_alias 字段！' },
  msg_tpl_alias_wrong: { zh: '模板 group_alias 与合作方模板不一致，请检查！' },
  msg_tpl_is_left_wrong: { zh: '模板 is_left 值须为{{value}}，请检查' },
  msg_peer_config_failed: { zh: '获取对侧工作流配置失败' },
  msg_peer_not_ready: { zh: '对侧配置未完成' },
  msg_not_config: { zh: '工作流配置未完成' },
  msg_workflow_name_invalid: { zh: '最长允许255个字符' },
  msg_sure_to_stop: { zh: '确认停止运行该工作流吗?' },
  msg_sure_to_delete: { zh: '确认删除吗?' },
  msg_unforkable: { zh: '根据对侧配置，该工作流不允许被复制，请与对侧沟通后再试' },
  msg_get_peer_cfg_failed: { zh: '获取对侧配置失败: ' },
  msg_reuse_noti: { zh: '{{name}} 改为继承状态后，后续依赖 {{name}} 的任务都将重置为“继承”状态' },
  msg_non_reuse_noti: {
    zh: '{{name}} 改为不继承状态后，后续依赖  {{name}} 的任务都将切换成为“不继承”状态',
  },
  msg_upstreaming_nonreusable: { zh: '因存在上游依赖不继承，无法修改此任务继承与否' },
  msg_chart_deps_loading: { zh: '图表依赖正在加载，请稍等' },
  msg_get_tpl_detail_failed: { zh: '获取模板详情失败，请稍后再试' },
  msg_group_required: { zh: '请输入 Group 名' },
  msg_jobname_required: { zh: '请输入 Job 名' },
  msg_yaml_required: { zh: '请加入 YAML 模版' },
  msg_varname_required: { zh: '请输入变量 Key' },
  msg_varname_invalid: { zh: '只允许大小写英文字母数字及下划线的组合' },
  msg_del_job_warning: { zh: '删除后，该 Job 配置的内容都将丢失' },
  msg_metric_public: { zh: '公开后，对侧将能查看你的「任务运行结果指标」' },
  msg_toggle_job_disabled: { zh: '是否启用该Job' },
  msg_diable_job_will_cause: { zh: '工作流执行时将直接跳过该Job' },
  msg_lack_workflow_infos: { zh: '缺少Workflow信息' },
  msg_schduled_run: {
    zh: '重训功能目前只针对左模板生效，启用该功能将间隔性地重跑 Workflow，如有疑问请联系开发人员',
  },
  msg_sure_2_replace_tpl: { zh: '确认更换模板吗' },
  msg_loose_origin_vars_vals: { zh: '更换后原模板的配置值将丢失' },
  msg_resued_job_cannot_edit: { zh: '已继承结果的任务将无法更改变量' },
  msg_resued_job: { zh: '该任务直接复用了前次运行的结果' },
  msg_no_available_kibana: { zh: '查询结果为空' },

  title_toggle_reusable: { zh: '切换至{{state}}状态' },

  var_auth_write: { zh: '可编辑' },
  var_auth_read: { zh: '可见' },
  var_auth_private: { zh: '不可见' },

  step_basic: { zh: '基础配置' },
  step_tpl_basic: { zh: '基础信息' },
  step_config: { zh: '工作流配置' },
  step_tpl_config: { zh: '任务配置' },

  job_node_pending: { zh: ' 待配置' },
  job_node_configuring: { zh: '配置中' },
  job_node_config_completed: { zh: '配置完成' },
  job_node_unfinished: { zh: '未完成配置' },
  job_node_invalid: { zh: '配置有误' },
  job_node_success: { zh: '运行成功' },
  job_node_waiting: { zh: '待运行' },
  job_node_failed: { zh: '运行失败' },
  job_node_running: { zh: '运行中' },
  job_node_stop_running: { zh: '手动停止运行' },
  job_node_stopped: { zh: '已停止' },
  job_node_reused: { zh: '已继承' },
  job_node_disabled: { zh: '已禁用' },

  pod_unknown: { zh: '状态未知' },
  pod_failed_cleared: { zh: '失败&已清理资源' },
  pod_success_cleared: { zh: '成功&已释放资源' },
};

export default separateLng(workflow);
