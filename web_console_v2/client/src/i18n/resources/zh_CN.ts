import project from './modules/project';
import workflow from './modules/workflow';
import login from './modules/login';
import menu from './modules/menu';
import error from './modules/error';
import upload from './modules/upload';
import term from './modules/term';
import app from './modules/app';
import dataset from './modules/dataset';
import settings from './modules/settings';
import users from './modules/users';
import intersection_dataset from './modules/intersection_dataset';
import validError from './modules/validError';
import modelCenter from './modules/modelCenter';
import modelServing from './modules/modelServing';
import audit from './modules/audit';
import algorithmManagement from './modules/algorithmManagement';
import operation_maintenance from './modules/operation_maintenance';
import dashboard from './modules/dashboard';
import trusted_center from './modules/trustedCenter';

const messages = {
  translation: {
    upload: upload.zh,
    term: term.zh,
    error: error.zh,
    login: login.zh,
    menu: menu.zh,
    project: project.zh,
    app: app.zh,
    workflow: workflow.zh,
    dataset: dataset.zh,
    settings: settings.zh,
    users: users.zh,
    valid_error: validError.zh,
    model_center: modelCenter.zh,
    intersection_dataset: intersection_dataset.zh,
    model_serving: modelServing.zh,
    audit: audit.zh,
    algorithm_management: algorithmManagement.zh,
    operation_maintenance: operation_maintenance.zh,
    dashboard: dashboard.zh,
    trusted_center: trusted_center.zh,

    all: '全部',
    terms: '服务协议',
    privacy: '隐私条款',
    more: '更多',
    confirm: '确认',
    submit: '确认',
    cancel: '取消',
    close: '关闭',
    edit: '编辑',
    scale: '扩缩容',
    delete: '删除',
    reset: '重置',
    stop: '停止',
    terminate: '终止',
    previous_step: '上一步',
    next_step: '下一步',
    operation: '操作',
    certificate: '证书',
    click_to_retry: '点此重试',
    creator: '创建者',
    created_at: '创建时间',
    started_at: '开始时间',
    stop_at: '结束时间',
    running_duration: '运行时长',
    yes: '是',
    no: '否',
    pls_try_again_later: '请稍后重试',
    id: 'ID',
    updated_at: '更新时间',
    deleted_at: '删除时间',
    hint_total_table: '共 {{total}} 条记录',
    msg_quit_warning: '取消后，已配置内容将不再保留',
    create: '创建',
    save: '保存',
    send_request: '发送请求',
    send: '发送',
    more_info: '更多信息',

    placeholder_input: '请输入',
    placeholder_select: '请选择',
    placeholder_required: '必填项',

    hint_total_select: '已选择 {{total}} 项',
    select_all: '全选',

    label_time_asc: '按时间升序',
    label_time_desc: '按时间降序',

    detail: '详情',
    favorite_success: '收藏成功',
    favorite_fail: '收藏失败',
    cancel_favorite_success: '取消收藏成功',
    cancel_favorite_fail: '取消收藏失败',
    export: '导出',
    exporting: '正在导出',
    export_result: '结果导出',

    success: '成功',
    fail: '失败',
    evaluating: '评估中',
    predicting: '预测中',
    waitConfirm: '待确认',
    pass: '通过',
    reject: '拒绝',

    add: '添加',
    change: '变更',

    message_create_success: '创建成功',
    message_create_fail: '创建失败',
    message_modify_success: '修改成功',
    message_modify_fail: '修改失败',
    message_delete_success: '删除成功',
    message_delete_fail: '删除失败',
    message_no_file: '没有文件',
    message_publish_success: '发布成功',
    message_publish_failed: '发布失败',
    message_authorize_success: '授权成功',
    message_authorize_failed: '授权失败',
    message_revoke_success: '撤销成功',
    message_revoke_failed: '撤销失败',
    message_stop_success: '停止成功',
    message_stop_fail: '停止失败',
    message_name_duplicated: '名称已存在',
    message_export_loading: '正在导出',
    message_export_success: '导出成功',
    message_export_fail: '导出失败',

    transfer_total: '全部共 {{total}} 项',
    transfer_select_total: '已选 {{selectedCount}}/{{total}} 项',

    open_code_editor: '打开代码编辑器',
    code_editor: '代码编辑器',
    no_data: '暂无数据',
    no_label: '无标签',

    copy: '复制',
    back: '返回',
    check: '查看',
    publish: '发布',
    revoke: '撤销',

    create_folder: '创建子文件夹',
    create_file: '创建子文件',
    create_folder_on_root: '创建根路径文件夹',
    create_file_on_root: '创建根路径文件',

    select_project_notice: '请选择工作区',

    msg_quit_modal_title: '确认要退出？',
    msg_quit_modal_content: '退出后，当前所填写的信息将被清空。',

    hyper_parameters: '超参数',

    tip_please_input_positive_integer: '请输入正整数',
    tip_please_input_positive_number: '请输入正数，小数点后保留1位',
    tip_replicas_range: '实例数范围1～100',
    tip_peer_unauthorized: '{{participantName}}暂未授权，请线下联系处理',

    cpu: 'CPU',
    mem: '内存',
    replicas: '实例数',

    placeholder_cpu: '输入CPU规格',
    placeholder_mem: '输入内存规格',

    label_horizontal_federalism: '横向联邦',
    label_vertical_federalism: '纵向联邦',
    coordinator: '本方',
    participant: '合作伙伴',

    term_type: '类型',
    term_federal_type: '联邦类型',
    term_model: '模型',
    term_dataset: '数据集',
    term_resource_config: '资源配置',
    term_algorithm_type: '算法类型',
    term_model_type_nn_vertical: '纵向联邦-NN模型',
    term_model_type_nn_horizontal: '横向联邦-NN模型',
    term_model_type_tree_vertical: '纵向联邦-树模型',
    term_favored: '已收藏',
    term_unfavored: '未收藏',
    term_name: '名称',
    term_compare: '对比',

    term_true: '是',
    term_false: '否',

    pod_id: '实例 ID',
    authorized: '已授权',
    unauthorized: '未授权',
    local_authorized: '本侧已授权',
    local_unauthorized: '本侧未授权',
    peer_authorized: '对侧已授权',
    peer_unauthorized: '对侧未授权',

    action_authorize: '授权',
    action_revoke: '撤销',
  },
};

export default messages;
