import { FC, useEffect } from 'react';
import { useParams, useLocation, useHistory } from 'react-router-dom';
import qs from 'qs';
import store from 'store2';
import { useTranslation } from 'react-i18next';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { FedLoginWay } from 'typings/auth';
import { global_login } from '../Login';
import { useSetRecoilState } from 'recoil';
import { userInfoQuery } from 'stores/user';
import { Message } from '@arco-design/web-react';

const SSOCallback: FC = () => {
  const { t } = useTranslation();
  const setUserInfo = useSetRecoilState(userInfoQuery);
  const history = useHistory();

  const { ssoName } = useParams<{
    ssoName: string;
  }>();

  const location = useLocation();

  const query = location.search || '';

  useEffect(() => {
    if (!ssoName || !query) {
      return;
    }

    // Parse url query
    const queryObject = qs.parse(query.slice(1)) || {}; // slice(1) to remove '?' prefix

    // Find current login way info
    const loginWayList: FedLoginWay[] = store.get(LOCAL_STORAGE_KEYS.app_login_way_list) || [];

    const currentLoginWay = loginWayList.find((item: FedLoginWay) => {
      return item.name === ssoName;
    });

    if (!currentLoginWay) {
      Message.error(
        t('login.error_not_find_sso_info', {
          ssoName,
        }),
      );
      return;
    }

    let codeKey = '';

    switch (currentLoginWay.protocol_type.toLocaleLowerCase()) {
      case 'cas':
        codeKey = currentLoginWay[currentLoginWay.protocol_type]?.['code_key'] || 'ticket';
        break;
      case 'oauth':
      case 'oauth2':
        codeKey = currentLoginWay[currentLoginWay.protocol_type]?.['code_key'] || 'code';
        break;
      default:
        codeKey = currentLoginWay[currentLoginWay.protocol_type]?.['code_key'] || 'code';
        break;
    }

    const ssoInfo = {
      ssoName: currentLoginWay.name,
      ssoType: currentLoginWay.protocol_type,
      ssoCode: queryObject[codeKey],
      codeKey,
    };

    // Store sso_info into localstorage, it will be used in Axios request interceptors as custom HTTP header, like 'x-pc-auth': <sso_name> <type> <credentials>
    store.set(LOCAL_STORAGE_KEYS.sso_info, ssoInfo);
    // If ssoName,ssoType,ssoCode existed, then call login api with code and sso_name
    if (ssoInfo.ssoName && ssoInfo.ssoType && ssoInfo.ssoCode && codeKey) {
      try {
        global_login(
          {
            [codeKey]: ssoInfo.ssoCode,
          },
          {
            sso_name: ssoName,
          },
          setUserInfo,
          history,
        );
      } catch (error) {
        Message.error(error.message);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ssoName, query]);

  return null;
};

export default SSOCallback;
