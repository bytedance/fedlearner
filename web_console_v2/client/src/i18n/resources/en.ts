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
    upload: upload.en,
    term: term.en,
    error: error.en,
    login: login.en,
    menu: menu.en,
    project: project.en,
    workflow: workflow.en,
    app: app.en,
    dataset: dataset.en,
    settings: settings.en,
    users: users.en,
    intersection_dataset: intersection_dataset.en,
    valid_error: validError.en,
    model_center: modelCenter.en,
    model_serving: modelServing.en,
    audit: audit.en,
    algorithm_management: algorithmManagement.en,
    operation_maintenance: operation_maintenance.en,
    dashboard: dashboard.en,
    trusted_center: trusted_center.en,

    all: 'All',
    terms: 'Terms of Services',
    privacy: 'Privacy Protocol',
    more: 'More',
    confirm: 'OK',
    submit: 'OK',
    cancel: 'Cancel',
    close: 'Close',
    edit: 'Edit',
    scale: 'Scale Service',
    delete: 'Delete',
    reset: 'Reset',
    stop: 'Stop',
    terminate: 'Terminate',
    operation: 'Operation',
    previous_step: 'previous step',
    next_step: 'Next step',
    certificate: 'Certificate',
    click_to_retry: 'Click to retry',
    yes: 'Yes',
    no: 'No',
    pls_try_again_later: 'Please try again later',
    id: 'ID',
    creator: 'Creator',
    created_at: 'CreatedTime',
    started_at: 'StartedTime',
    stop_at: 'StopTime',
    running_duration: 'Running duration',

    updated_at: 'UpdatedTime',
    deleted_at: 'DeletedTime',
    hint_total_table: 'Total {{total}} items',
    msg_quit_warning: 'After canceling, the configured content will no longer be retained',
    create: 'create',
    save: 'save',
    send_request: 'send request',
    more_info: 'more information',

    placeholder_input: 'Please input',
    placeholder_select: 'Please select',
    placeholder_required: 'Required',

    hint_total_select: '{{total}} items selected',
    select_all: 'select all',

    label_time_asc: 'Ascending by time',
    label_time_desc: 'Descending by time',

    detail: 'Detail',
    favorite_success: 'Favorite success',
    favorite_fail: 'Favorite fail',
    cancel_favorite_success: 'Cancel favorite success',
    cancel_favorite_fail: 'Cancel favorite fail',
    export: 'Export',
    exporting: 'Exporting',
    export_result: 'Export result',

    success: 'Success',
    fail: 'Fail',
    evaluating: 'Evaluating',
    predicting: 'Predicting',
    waitConfirm: 'WaitConfirm',
    pass: 'Pass',
    reject: 'Reject',

    add: 'Add',
    change: 'Change',
    publish: 'Publish',
    revoke: 'Revoke',

    message_create_success: 'Create success',
    message_create_fail: 'Create fail',
    message_modify_success: 'Modify success',
    message_modify_fail: 'Modify fail',
    message_delete_success: 'Delete success',
    message_delete_fail: 'Delete fail',
    message_no_file: 'No file',
    message_publish_success: 'Publish success',
    message_publish_failed: 'Publish failed',
    message_revoke_success: 'Revoke success',
    message_revoke_failed: 'Revoke failed',
    message_stop_success: 'Stop success',
    message_stop_fail: 'Stop fail',
    message_name_duplicated: 'Name duplicated',
    message_export_loading: 'Exporting...',
    message_export_success: 'Export success',
    message_export_fail: 'Export fail',

    transfer_total: 'Total {{total}} items',
    transfer_select_total: 'Select {{selectedCount}}/{{total}} items',

    open_code_editor: 'Open code editor',
    no_data: 'No data',
    no_label: 'No label',

    copy: 'Copy',
    back: 'Back',
    check: 'Check',

    create_folder: 'New Folder',
    create_file: 'New File',
    create_folder_on_root: 'New Folder on root',
    create_file_on_root: 'New File on root',

    select_project_notice: 'Please select a project',

    msg_quit_modal_title: 'Are you sure you want to quit?',
    msg_quit_modal_content: 'After quitting, the information currently filled in will be cleared.',

    hyper_parameters: 'Hyper parameters',

    tip_please_input_positive_integer: 'Please input positive integer',
    tip_please_input_positive_number:
      'Please input a positive number with 1 digit after the decimal point',
    tip_replicas_range: 'The number of replicas ranges from 1 to 100',
    tip_peer_unauthorized:
      '{{participantName}} is not authorized for the time being, please contact offline for handling',

    cpu: 'CPU',
    mem: 'MEM',
    replicas: 'Replicas',

    placeholder_cpu: 'Input CPU Specifications',
    placeholder_mem: 'Input memory Specifications',

    label_horizontal_federalism: 'Horizontal federalism',
    label_vertical_federalism: 'Vertical federalism',

    term_type: 'type',
    term_federal_type: 'Federal type',
    term_model: 'Model',
    term_dataset: 'Dataset',
    term_resource_config: 'Resource config',
    term_algorithm_type: 'Algorithm Type',
    term_model_type_nn_vertical: 'NN Vertical',
    term_model_type_nn_horizontal: 'NN Horizontal',
    term_model_type_tree_vertical: 'Tree Vertical',
    term_true: 'Yes',
    term_false: 'No',

    pod_id: 'Pod id',
    authorized: 'authorized',
    unauthorized: 'unauthorized',
    local_authorized: 'This side has been authorized',
    local_unauthorized: 'This side is not authorized',
    peer_authorized: 'The opposite side is authorized',
    peer_unauthorized: 'The opposite side is not authorized',
  },
};

export default messages;
