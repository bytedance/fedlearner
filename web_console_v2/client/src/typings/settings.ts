export type SettingOptions = {
  webconsole_image?: string;
  variables?: SystemVariable[];
};

export type ValueType =
  | 'STRING'
  | 'INT'
  | 'LIST'
  | 'OBJECT'
  | 'NUMBER'
  | 'BOOL'
  | 'BOOLEAN'
  | 'CODE';
export interface SystemVariable {
  name: string;
  value: any;
  /** If fixed = true, can't modify name and delete myself */
  fixed: boolean;
  value_type: ValueType;
}

export interface SettingInfo {
  uniq_key: string;
  value: string;
  created_at?: DateTime;
  updated_at?: DateTime;
}

export interface SettingVariables {
  variables?: SystemVariable[];
}

export interface SystemInfo {
  name: string;
  domain_name: string;
  pure_domain_name?: string;
}
