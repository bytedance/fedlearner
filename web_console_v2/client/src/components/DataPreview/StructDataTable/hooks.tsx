/* istanbul ignore file */

import { useEffect } from 'react';
import { STRUCT_DATA_TABLE_ID } from '.';
import { FEATURE_DRAWER_ID } from './FeatureInfoDrawer';

export function useFeatureDrawerClickOutside(params: {
  setActiveFeatKey: (key?: string) => void;
  toggleDrawerVisible: (val: boolean) => void;
  allowlistElementIds?: string[];
}) {
  useEffect(() => {
    document.addEventListener('click', handler);

    function handler(evt: MouseEvent) {
      const target = evt.target as HTMLElement;
      if (
        !document.getElementById(STRUCT_DATA_TABLE_ID)?.contains(target) &&
        !document.getElementById(FEATURE_DRAWER_ID)?.contains(target)
      ) {
        params.setActiveFeatKey(undefined);
        params.toggleDrawerVisible(false);
      }
    }

    return () => {
      document.removeEventListener('click', handler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.setActiveFeatKey, params.toggleDrawerVisible]);
}
