/* istanbul ignore file */

import { useRecoilValue } from 'recoil';
import i18n from 'i18n';

import { appFlag } from 'stores/app';
import { useIsAdminRole } from 'hooks/user';

import { FlagKey } from 'typings/flag';

export function useGetIsCanEditTemplate(isPresetTemplate = false) {
  const appFlagValue = useRecoilValue(appFlag);
  const isAdminRole = useIsAdminRole();

  const isCanEdit =
    !isPresetTemplate ||
    (isPresetTemplate &&
      isAdminRole &&
      Boolean(appFlagValue[FlagKey.PRESET_TEMPLATE_EDIT_ENABLED]));

  const tip = isCanEdit
    ? ''
    : !appFlagValue[FlagKey.PRESET_TEMPLATE_EDIT_ENABLED]
    ? i18n.t('workflow.msg_can_not_edit_preset_template')
    : i18n.t('workflow.msg_only_admin_edit_preset_template');

  return { isCanEdit, tip };
}
