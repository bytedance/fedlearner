import { FC, useEffect } from 'react';
import { useHistory, useLocation } from 'react-router-dom';
import qs from 'qs';
import store from 'store2';
import { useTranslation } from 'react-i18next';
import { useSetRecoilState } from 'recoil';
import { useUnmount } from 'react-use';

import { userInfoQuery } from 'stores/user';
import { getMyUserInfo } from 'services/user';

import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';

import { Message } from '@arco-design/web-react';

const TokenCallback: FC = () => {
  const { t } = useTranslation();

  const history = useHistory();
  const location = useLocation();

  const setUserInfo = useSetRecoilState(userInfoQuery);

  const query = location.search || '';

  useEffect(() => {
    if (!query) {
      Message.error(t('login.error_not_find_access_token'));
      store.remove(LOCAL_STORAGE_KEYS.temp_access_token);
      return;
    }

    // Parse url query
    const queryObject = qs.parse(query.slice(1)) || {}; // slice(1) to remove '?' prefix

    // Get access_token info from queryObject
    const accessToken = decodeURIComponent((queryObject['access_token'] as string) ?? '');

    if (!accessToken) {
      Message.error(t('login.error_not_find_access_token'));
      store.remove(LOCAL_STORAGE_KEYS.temp_access_token);
      return;
    }

    // Store accessToken into localstorage, it will be used in Axios request interceptors as HTTP header, like Authorization = `Bearer ${token}`
    store.set(LOCAL_STORAGE_KEYS.temp_access_token, accessToken);

    // Call API to get my userInfo
    getMyUserInfo()
      .then((resp) => {
        const { data } = resp;

        // Remove temp_access_token
        store.remove(LOCAL_STORAGE_KEYS.temp_access_token);

        // Store userInfo
        store.set(LOCAL_STORAGE_KEYS.current_user, {
          ...data,
          access_token: accessToken,
          date: Date.now(),
        });
        setUserInfo(data);

        Message.success(t('app.login_success'));

        if (queryObject.from) {
          history.replace(decodeURIComponent(queryObject.from as string) || '/projects');
          return;
        }

        history.replace('/projects');
      })
      .catch((error) => {
        store.remove(LOCAL_STORAGE_KEYS.temp_access_token);
        Message.error(error + '');
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  useUnmount(() => {
    store.remove(LOCAL_STORAGE_KEYS.temp_access_token);
  });

  return null;
};

export default TokenCallback;
