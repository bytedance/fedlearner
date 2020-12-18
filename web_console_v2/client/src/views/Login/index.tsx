import React, { useCallback } from 'react'
import styled from 'styled-components'
import { Input, Checkbox, Form, Button, message } from 'antd'
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons'
import loginLeftBg from 'assets/images/login-left-bg.jpg'
import logoWhite from 'assets/images/logo-white.svg'
import { MixinFlexAlignCenter } from 'styles/mixins'
import { login } from 'services/user'
import { useHistory } from 'react-router-dom'
import { useToggle } from 'react-use'
import { useTranslation } from 'react-i18next'
import store from 'store2'
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys'
import { FedLoginFormData } from 'typings/auth'

const Layout = styled.main`
  display: grid;
  grid-template-areas: 'left right';
  grid-template-columns: minmax(0, 37%) 1fr;
  min-width: 500px;
  height: 100vh;
  min-height: 500px;
  background-color: #fff;

  @media screen and (max-width: 1040px) {
    grid-template-columns: 1fr 520px;
  }
`

const Block = styled.section`
  height: 100%;
`

const Slogan = styled.h1`
  color: white;
  font-size: 50px;
  font-weight: bolder;
`

const Left = styled(Block)`
  ${MixinFlexAlignCenter()}

  display: flex;
  flex-direction: column;
  background: url(${logoWhite}) top 24px left 32px no-repeat,
    linear-gradient(270deg, rgba(40, 106, 244, 0.9) 0%, rgba(62, 151, 254, 0.9) 100%),
    url(${loginLeftBg}) no-repeat;
  background-size: 121px auto, contain, cover;

  @media screen and (max-width: 520px) {
    display: none;
  }
`

const Right = styled(Block)`
  ${MixinFlexAlignCenter()}

  display: flex;
  background-color: white;
`

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

  .aggrement {
    margin-top: 16px;
    color: #7a8499;
    font-size: 13px;
  }

  > .checkboxItem {
    margin-bottom: 0;
  }
`

const LoginFormButton = styled(Button)`
  width: 100%;
`

const LoginFormCheckbox = styled(Checkbox)`
  color: #7a8499;
`

function Login() {
  const history = useHistory()
  const { t } = useTranslation()
  const [submitting, toggleSubmit] = useToggle(false)

  const onSubmit = useCallback(
    async (payload: unknown) => {
      toggleSubmit(true)
      try {
        const { data } = await login(payload as FedLoginFormData)

        store.set(LOCAL_STORAGE_KEYS.current_user, { ...data, date: Date.now() })

        history.push('/')
      } catch (error) {
        message.error(error.message)
      }
      toggleSubmit(false)
    },
    [toggleSubmit, history],
  )

  return (
    <Layout>
      <Left>
        <Slogan>{t('login_slogan')}</Slogan>
      </Left>

      <Right>
        <LoginForm
          size="large"
          name="login-form"
          initialValues={{ remember: true }}
          onFinish={onSubmit}
        >
          <h3 className="form-title">{t('login_form_title')}</h3>

          <Form.Item
            name="username"
            rules={[{ required: true, message: t('login_username_message') }]}
          >
            <Input name="username" placeholder={t('login_username_placeholder')} />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: t('login_password_message') }]}
          >
            <Input.Password
              placeholder={t('login_password_placeholder')}
              iconRender={(visible) => (visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />)}
            />
          </Form.Item>

          <Form.Item name="remember" valuePropName="checked" className="checkboxItem">
            <LoginFormCheckbox>记住登录状态</LoginFormCheckbox>
          </Form.Item>

          <Form.Item>
            <LoginFormButton loading={submitting} size="large" type="primary" htmlType="submit">
              {t('login_button')}
            </LoginFormButton>

            <p className="aggrement">
              {t('login_aggrement', {
                terms: `${t('terms')}`,
                privacy: `${t('privacy')}`,
                interpolation: { escapeValue: false },
              })}
            </p>
          </Form.Item>
        </LoginForm>
      </Right>
    </Layout>
  )

  // -------- Handlers ------------
}

export default Login
