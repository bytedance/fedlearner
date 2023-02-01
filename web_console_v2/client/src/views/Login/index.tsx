import React, { FC, useEffect, useState } from 'react';
import { Input, Checkbox, Form, Button, Message } from '@arco-design/web-react';
import loginIllustration from 'assets/images/login-illustration.png';
import { login, fetchLoginWayList } from 'services/user';
import { Redirect, useHistory } from 'react-router-dom';
import { useToggle } from 'react-use';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { FedLoginFormData, FedLoginQueryParamsData } from 'typings/auth';
import { useRecoilQuery } from 'hooks/recoil';
import { useGetLogoSrc, useUrlState, useGetThemeBioland } from 'hooks';
import { userInfoQuery } from 'stores/user';
import { useSetRecoilState, useRecoilState, useRecoilValue } from 'recoil';
import { parseSearch } from 'shared/url';
import { appPreference, appEmailGetters, appLoginWayList } from 'stores/app';
import { fetchSysEmailGroup } from 'services/settings';
import { useQuery } from 'react-query';
import { FedLoginWay } from 'typings/auth';
import iconSSODefault from 'assets/icons/icon-sso-oauth-default.svg'; // default is oauth icon
import iconOAuthDefault from 'assets/icons/icon-sso-oauth-default.svg';
import logoCASDefault from 'assets/images/logo-sso-cas-default.jpeg';
import * as H from 'history';
import styled from './index.module.less';

function getDefaultLoginWayIcon(protocolType: string) {
  let icon: string = iconSSODefault;

  switch (protocolType.toLocaleLowerCase()) {
    case 'cas':
      icon = logoCASDefault;
      break;
    case 'oauth':
    case 'oauth2':
      icon = iconOAuthDefault;
      break;
    default:
      icon = iconSSODefault;
      break;
  }

  return icon;
}

const Login: FC = () => {
  const history = useHistory();
  const [submitting, toggleSubmit] = useToggle(false);

  const query = useRecoilQuery(userInfoQuery);
  const setUserInfo = useSetRecoilState(userInfoQuery);
  const [preference, setPreference] = useRecoilState(appPreference);
  const [loginWayList, setLoginWayList] = useRecoilState(appLoginWayList);
  const email = useRecoilValue(appEmailGetters);
  const isBioland = useGetThemeBioland();

  const [isShowLoginWayList, setIsShowLoginWayList] = useState(false);

  const { primaryLogo } = useGetLogoSrc();

  const [urlState] = useUrlState();

  useQuery(['fetchSysEmailGroup'], () => fetchSysEmailGroup(), {
    retry: 2,
    refetchOnWindowFocus: false,
    onSuccess(data) {
      const emailValue = data.data.value;
      setPreference({
        ...preference,
        sysEmailGroup: emailValue,
      });
    },
  });

  useQuery(['fetchLoginWayList'], () => fetchLoginWayList(), {
    retry: 2,
    refetchOnWindowFocus: false,
    onSuccess(data) {
      setLoginWayList(data.data || []);
    },
  });

  useEffect(() => {
    const handler = async (event: MessageEvent<any>) => {
      if (event.origin !== window.location.origin) return;

      if (!event.data || !event.data.ssoInfo) {
        return;
      }
      const { ssoInfo } = event.data;

      const { ssoName, ssoType, ssoCode, codeKey } = ssoInfo;

      // If ssoName,ssoType,ssoCode existed, then call login api with code and sso_name
      if (ssoName && ssoType && ssoCode && codeKey) {
        try {
          global_login(
            {
              [codeKey]: ssoCode,
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
    };

    window.addEventListener('message', handler, false);

    if (urlState.auto_login) {
      triggerSSOAuto(urlState.auto_login);
    }

    return () => {
      window.removeEventListener('message', handler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (query.data?.id) {
    return <Redirect to="/projects" />;
  }

  return (
    <main className={styled.login_layout}>
      <section
        className={styled.login_left_block}
        style={{
          backgroundImage: `url(${primaryLogo}), url(${loginIllustration})`,
        }}
      />
      <section className={isBioland ? styled.login_bioland_right_block : styled.login_right_block}>
        <Form
          className={styled.login_form}
          size="large"
          name="login-form"
          initialValues={{ remember: true }}
          onSubmit={onSubmit}
        >
          <h3 className={styled.form_title}>账号登录</h3>

          <Form.Item field="username" rules={[{ required: true, message: '请输入用户名!' }]}>
            <Input allowClear name="username" placeholder="用户名/邮箱" />
          </Form.Item>

          <Form.Item field="password" rules={[{ required: true, message: '请输入密码!' }]}>
            <Input.Password
              allowClear
              placeholder="密码"
              // iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
            />
          </Form.Item>

          <Form.Item field="remember" className="checkboxItem">
            <Checkbox defaultChecked={true}>记住登录状态</Checkbox>
          </Form.Item>

          <Form.Item>
            <Button
              className={styled.login_button}
              loading={submitting}
              size="large"
              type="primary"
              htmlType="submit"
            >
              登陆
            </Button>

            <p className={styled.no_account}>
              {`如无账号，请发送申请邮件至管理员邮箱 ${email || 'privacy_computing@bytedance.com'}`}
            </p>
          </Form.Item>

          {loginWayList && loginWayList.length > 0 && (
            <span className={styled.other_login_way_text} onClick={onOtherLoginWayClick}>
              {isShowLoginWayList ? '隐藏其他登陆方式' : '其他登陆方式'}
            </span>
          )}
          {isShowLoginWayList && (
            <div className={styled.login_way_layout}>
              {loginWayList.map((item) => {
                return (
                  <div
                    className={styled.login_way_item}
                    key={item.display_name}
                    onClick={() => {
                      onLoginWayClick(item);
                    }}
                  >
                    <img
                      src={item.icon_url || getDefaultLoginWayIcon(item.protocol_type)}
                      alt={item.display_name}
                    />
                    <div>{item.display_name}</div>
                  </div>
                );
              })}
            </div>
          )}
        </Form>
      </section>
    </main>
  );

  // -------- Handlers ------------

  function onOtherLoginWayClick() {
    setIsShowLoginWayList((prevState) => !prevState);
  }

  async function onSubmit(payload: any) {
    toggleSubmit(true);
    try {
      payload.password = btoa(payload.password!);

      global_login(payload, {}, setUserInfo, history);
    } catch (error) {
      Message.error(error.message);
    }
    toggleSubmit(false);
  }

  function onLoginWayClick(loginWayInfo: FedLoginWay) {
    const protocolType = loginWayInfo.protocol_type;
    const { authorize_url } = loginWayInfo[protocolType] || {};
    let authorizeUrl = authorize_url;

    // If authorize_url is provided, just use authorize_url that had assembled in Back-end.
    // Otherwise, assemble it in Front-end.
    if (!authorizeUrl) {
      if (protocolType && protocolType.toLowerCase() === 'cas') {
        const { cas_server_url, login_route, service_url } = loginWayInfo[protocolType];
        authorizeUrl = `${cas_server_url}${login_route}?service=${encodeURIComponent(service_url)}`;
      }
    }
    if (authorizeUrl) {
      window.open(authorizeUrl, '_self');
    } else {
      Message.error('找不到即将跳转的 url 信息');
    }
  }

  function triggerSSOAuto(auto_login: string) {
    const SSOInfo = loginWayList.find((item) => item.name === auto_login);
    if (SSOInfo) {
      onLoginWayClick(SSOInfo);
    }
  }
};

export async function global_login(
  payload: FedLoginFormData,
  queryParam: FedLoginQueryParamsData = {},
  setUserInfo: (userInfo: any) => void,
  history: H.History,
) {
  try {
    const { data } = await login(payload as FedLoginFormData, queryParam);
    store.set(LOCAL_STORAGE_KEYS.current_user, {
      ...data.user,
      access_token: data.access_token,
      date: Date.now(),
    });
    setUserInfo(data.user);
    Message.success('登录成功');
    //TODO: the from history will be lost when login by SSO and can not jump to the page before login;
    const from = parseSearch(history.location).get('from');
    history.push(decodeURIComponent(from || '/projects'));
  } catch (error) {
    const { sso_name } = queryParam;
    if (sso_name) {
      Message.error(`${sso_name}登录验证失败！`);
    } else {
      Message.error(error + '');
    }
  }
}

export default Login;
