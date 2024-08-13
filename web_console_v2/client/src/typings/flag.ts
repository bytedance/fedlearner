export enum FlagKey {
  USER_MANAGEMENT_ENABLED = 'user_management_enabled',
  LOGO_URL = 'logo_url',
  PRESET_TEMPLATE_EDIT_ENABLED = 'preset_template_edit_enabled',
  BCS_SUPPORT_ENABLED = 'bcs_support_enabled',
  TRUSTED_COMPUTING_ENABLED = 'trusted_computing_enabled',
  DASHBOARD_ENABLED = 'dashboard_enabled',
  DATASET_STATE_FIX_ENABLED = 'dataset_state_fix_enabled',
  HASH_DATA_JOIN_ENABLED = 'hash_data_join_enabled',
  HELP_DOC_URL = 'help_doc_url',
  REVIEW_CENTER_CONFIGURATION = 'review_center_configuration',
  MODEL_JOB_GLOBAL_CONFIG_ENABLED = 'model_job_global_config_enabled',
}

export interface Flag {
  [FlagKey.USER_MANAGEMENT_ENABLED]: boolean;
  [FlagKey.LOGO_URL]: string;
  [FlagKey.PRESET_TEMPLATE_EDIT_ENABLED]: boolean;
  [FlagKey.BCS_SUPPORT_ENABLED]: boolean;
  [FlagKey.TRUSTED_COMPUTING_ENABLED]: boolean;
  [FlagKey.DASHBOARD_ENABLED]: boolean;
  [FlagKey.DATASET_STATE_FIX_ENABLED]: boolean;
  [FlagKey.HASH_DATA_JOIN_ENABLED]: boolean;
  [FlagKey.MODEL_JOB_GLOBAL_CONFIG_ENABLED]: boolean;
  [FlagKey.HELP_DOC_URL]: string;
  [FlagKey.REVIEW_CENTER_CONFIGURATION]: string;
  [key: string]: boolean | string;
}
