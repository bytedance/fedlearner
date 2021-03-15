import request from 'libs/request';
import { SettingOptions } from 'typings/settings';

export function fetchSettings(): Promise<{ data: SettingOptions }> {
  return request('/v2/settings');
}

export function updateSettings(payload: SettingOptions): Promise<{ data: any }> {
  return request.patch('/v2/settings', payload);
}
