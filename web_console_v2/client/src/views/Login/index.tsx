import React, { FC } from 'react';
import styled from 'styled-components';
import { Input, Checkbox, Form, Button, message } from 'antd';
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import loginLeftBg from 'assets/images/login-left-bg.jpg';
import logoWhite from 'assets/images/logo-white.svg';
import logColorful from 'assets/images/logo-colorful.svg';
import { MixinFlexAlignCenter } from 'styles/mixins';
import { login } from 'services/user';
import { Redirect, useHistory } from 'react-router-dom';
import { useToggle } from 'react-use';
import { useTranslation } from 'react-i18next';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { FedLoginFormData } from 'typings/auth';
import { useRecoilQuery } from 'hooks/recoil';
import { userInfoQuery } from 'stores/user';
import { useSetRecoilState } from 'recoil';
import i18n from 'i18n';

const Layout = styled.main`
  display: grid;
  grid-template-areas: 'left right';
  grid-template-columns: 520px 1fr;
  min-width: 500px;
  height: 100vh;
  min-height: 500px;
  background-color: #fff;

  @media screen and (max-width: 1000px) {
    grid-template-columns: 0 1fr;
  }
`;
const Block = styled.section`
  position: relative;
  height: 100%;
`;
const Left = styled(Block)`
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  background: url(${logoWhite}) top 24px left 32px no-repeat,
    linear-gradient(270deg, rgba(40, 106, 244, 0.9) 0%, rgba(62, 151, 254, 0.9) 100%),
    url(${loginLeftBg}) no-repeat;
  background-size: 121px auto, contain, cover;

  > * {
    transform: translateY(-9vh);
  }
`;
const Slogan = styled.h1`
  width: 80%;
  margin-bottom: 0;
  color: white;
  font-size: 50px;
  font-weight: bolder;
`;
const Vision = styled.small`
  width: 80%;
  font-size: 16px;
  line-height: 22px;
  color: white;
`;
const Right = styled(Block)`
  ${MixinFlexAlignCenter()}

  display: flex;
  background-color: white;

  @media screen and (max-width: 1000px) {
    background: url(${logColorful}) top 24px left 32px no-repeat;
  }
`;
const LoginForm = styled(Form)`
  width: 360px;

  > .form-title {
    margin-bottom: 24px;
    font-size: 27px;
    line-height: 36px;
  }
  > .ant-space {
    display: flex;
  }
  .no-account {
    margin-top: 16px;
    color: var(--textColorSecondary);
    font-size: 12px;
    white-space: nowrap;
  }
  > .checkboxItem {
    margin-bottom: 0;
  }
`;
const LoginFormButton = styled(Button)`
  width: 100%;
  height: 48px;
  background-image: linear-gradient(270deg, #286af4 0%, #3e97fe 100%);
`;
const LoginFormCheckbox = styled(Checkbox)`
  color: #7a8499;
`;

const Login: FC = () => {
  const history = useHistory();
  const { t } = useTranslation();
  const [submitting, toggleSubmit] = useToggle(false);
  const setUserInfo = useSetRecoilState(userInfoQuery);

  const userQuery = useRecoilQuery(userInfoQuery);

  if (userQuery.data?.id) {
    return <Redirect to="/projects" />;
  }

  return (
    <Layout>
      <Left>
        <Slogan>{t('login.slogan')}</Slogan>
        <Vision>{t('login.vision')}</Vision>
      </Left>

      <Right>
        <LoginForm
          size="large"
          name="login-form"
          initialValues={{ remember: true }}
          onFinish={onSubmit}
        >
          <h3 className="form-title">{t('login.form_title')}</h3>

          <Form.Item
            name="username"
            rules={[{ required: true, message: t('login.username_message') }]}
          >
            <Input allowClear name="username" placeholder={t('login.username_placeholder')} />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: t('login.password_message') }]}
          >
            <Input.Password
              allowClear
              placeholder={t('login.password_placeholder')}
              iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
            />
          </Form.Item>

          <Form.Item name="remember" valuePropName="checked" className="checkboxItem">
            <LoginFormCheckbox>{t('login.remember')}</LoginFormCheckbox>
          </Form.Item>

          <Form.Item>
            <LoginFormButton loading={submitting} size="large" type="primary" htmlType="submit">
              {t('login.button')}
            </LoginFormButton>

            <p className="no-account">
              {t('login.no_account_tip', {
                email: 'admin@fedlearner.com',
              })}
            </p>
          </Form.Item>
        </LoginForm>
      </Right>
    </Layout>
  );

  // -------- Handlers ------------

  async function onSubmit(payload: unknown) {
    toggleSubmit(true);
    try {
      const data = await login(payload as FedLoginFormData);
      store.set(LOCAL_STORAGE_KEYS.current_user, { ...data, date: Date.now() });
      setUserInfo(data);
      message.success(i18n.t('app.login_success'));

      history.push('/projects');
    } catch (error) {
      message.error(error.message);
    }
    toggleSubmit(false);
  }
};

export default Login;
