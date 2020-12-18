const errors = {
  please_sign_in: '请登录',
}
const project = {
  create: '创建项目',
  describe:
    '提供项目的新增和管理功能，支持对项目进行新增、编辑、查询、删除功能，可查看一个项目下的联邦工作流任务列表、模型列表、API列表，一个项目下可创建多个联邦工作流任务。',
  search_placeholder: '输入项目名称关键词搜索',
  display_card: '卡片视图',
  display_list: '表格视图',
  connection_status_success: '成功',
  connection_status_waiting: '待检查',
  connection_status_checking: '检查中',
  connection_status_failed: '失败',
  action_edit: '编辑',
  action_detail: '详情',
  check_connection: '检查连接',
  create_work_flow: '创建工作流',
  connection_status: '连接状态',
  workflow_number: '工作流任务数量',
  name: '项目名称',
  participant_name: '合作伙伴名称',
  participant_url: '合作伙伴节点地址',
  participant_domain: '泛域名',
  remarks: '说明备注',
  name_placeholder: '请填写项目名称',
  participant_name_placeholder: '请填写合作伙伴名称',
  participant_url_placeholder: '请填写合作伙伴节点地址',
  participant_domain_placeholder: '请填写泛域名',
  remarks_placeholder: '请填写说明备注',
  name_message: '请填写项目名称！',
  participant_name_message: '请填写合作伙伴名称！',
  participant_url_message: '请填写合作伙伴节点地址！',
  participant_domain_message: '请填写泛域名！',
  edit: '编辑项目',
  workflow: '工作流任务',
  mix_dataset: '融合数据集',
  model: '模型',
  creator: '创建者',
  creat_time: '创建时间',
  add_parameters: '添加参数',
  env_path_config: '环境变量配置',
  show_env_path_config: '环境变量参数配置',
  hide_env_path_config: '收起环境变量配置',
  basic_information: '基本信息',
  participant_information: '合作伙伴信息',
  upload_certificate: '上传证书',
  backend_config_certificate: '后台手动配置',
  upload_certificate_placeholder: '请上传gz格式文件，大小不超过20MB',
  upload_certificate_message: '请上传证书',
  drag_to_upload: '拖拽到这里进行上传',
}

const login = {
  slogan: '标语占位',
  form_title: '账号登录',
  username_message: '请输入用户名!',
  username_placeholder: '用户名/邮箱',
  password_message: '请输入密码!',
  password_placeholder: '密码',
  remember: '记住登录状态',
  button: '登录',
  aggrement: '登录即表示同意 {{- terms}} 和 {{privacy}}',
}

const menu = {
  label_project: ' 项目管理',
  label_workflow: '工作流管理',
  label_datasets: '数据管理',
}

const messages = {
  translation: {
    errors,
    project,
    login,
    menu,

    terms: '服务协议',
    privacy: '隐私条款',
    more: '更多',
    submit: '确认',
    cancel: '取消',
    operation: '操作',
    certificate: '证书',
  },
}

export default messages
