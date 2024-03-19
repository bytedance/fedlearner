import request from 'libs/request';
import { SettingOptions, SettingInfo, SystemInfo, SettingVariables } from 'typings/settings';

export function fetchSettingsImage(): Promise<{ data: SettingInfo }> {
  return request('/v2/settings/webconsole_image');
}

export function fetchSettingVariables(): Promise<{ data: SettingVariables }> {
  return request('/v2/settings/system_variables');
}
export function updateSettingVariables(
  payload: SettingVariables,
): Promise<{ data: SettingVariables }> {
  return request.post('/v2/settings:update_system_variables', payload);
}

export function updateImage(payload: SettingOptions): Promise<{ data: SettingOptions }> {
  return request.post('/v2/settings:update_image', payload);
}

export function fetchSysEmailGroup(): Promise<{ data: SettingInfo }> {
  return request('/v2/settings/sys_email_group');
}

export function fetchSysInfo(): Promise<{ data: SystemInfo }> {
  return request('/v2/settings/system_info');
}
