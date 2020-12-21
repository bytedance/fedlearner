const errors = {
  please_sign_in: 'Pelase Sign in',
}
const project = {
  create: 'Create project',
  describe:
    'Provide project addition and management functions, support adding, editing, querying, and deleting projects. You can view the federal workflow task list, model list, and API list under a project. Multiple federal tasks can be created under a project Stream tasks.',
  search_placeholder: 'Enter the project name or keyword to search',
  display_card: 'Card view',
  display_list: 'Table view',
  connection_status_success: 'Success',
  connection_status_waiting: 'To be checked',
  connection_status_checking: 'Checking',
  connection_status_failed: 'Failed',
  action_edit: 'Edit',
  action_detail: 'Detail',
  check_connection: 'Check connection',
  create_work_flow: 'Create a workflow',
  connection_status: 'Connection status',
  workflow_number: 'Total workflows',
  name: 'Project name',
  participant_name: 'Participant name',
  participant_url: 'Participant node address',
  remarks: 'Remarks',
  name_placeholder: 'Please enter name',
  participant_name_placeholder: 'Please enter participant name',
  participant_url_placeholder: 'Please enter participant node address',
  remarks_placeholder: 'Please enter remarks',
  name_message: 'Please enter name!',
  participant_name_message: 'Please enter participant name!',
  participant_url_message: 'Please enter participant node address!',
  edit: 'Edit project',
  workflow: 'Workflow task',
  mix_dataset: 'Fusion data set',
  model: 'Model',
  creator: 'Creator',
  creat_time: 'Creation time',
  add_parameters: 'Add parameters',
  env_path_config: 'Environment variable configuration',
  show_env_path_config: 'Expand environment variable configuration',
  hide_env_path_config: 'Collapse environment variable configuration',
  basic_information: 'Basic Information',
  participant_information: 'Participant information',
  upload_certificate: 'Upload certificate',
  backend_config_certificate: 'Manual configuration in the backgend',
  upload_certificate_placeholder: 'Please upload a file in gz format, no more than 20MB in size',
  upload_certificate_message: 'Please upload the certificate',
  drag_to_upload: 'Drag and drop here to upload',
}

const login = {
  slogan: 'SLOGAN HERE',
  form_title: 'Sign in',
  username_message: 'Please enter username!',
  username_placeholder: 'Username / Phone number',
  password_message: 'Please enter password!',
  password_placeholder: 'Password',
  remember: 'Remember me',
  button: 'Sign in',
  aggrement: 'I accept and agree {{terms}} and {{privacy}}',
}

const menu = {
  label_project: 'Projects',
  label_workflow: 'Workflows',
  label_datasets: 'Datasets',
}

const workflows = {
  action_re_run: 'Re-run',
  action_run: '',
  action_stop_running: '',
  action_duplicate: '',
  action_detail: '',
}

const messages = {
  translation: {
    errors,
    project,
    login,
    menu,
    workflows,

    terms: 'Terms of Services',
    privacy: 'Privacy Protocol',
    more: 'More',
    submit: 'OK',
    cancel: 'Cancel',
    operation: 'Operation',
  },
}

export default messages
