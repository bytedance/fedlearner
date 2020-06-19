import React, { useState } from 'react';
import css from 'styled-jsx/css';
import { useRouter } from 'next/router';
import { Input, Button, Text, Note, Spacer, useInput, useTheme } from '@zeit-ui/react';
import UserIcon from '@zeit-ui/react-icons/user';
import Layout from '../components/Layout';
import { login } from '../services';

function useStyles(theme) {
  return css`
    .main {
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
    }

    .logo {
      margin: 32px 0 24px 0;
      cursor: pointer;
    }

    .form {
      width: 260px;
      max-width: 100%;
      margin-top: ${theme.layout.pageMargin};
    }
  `;
}

export default function Login() {
  const theme = useTheme();
  const styles = useStyles(theme);
  const router = useRouter();
  const [error, setError] = useState('');
  const { state: username, bindings: usernameBindings } = useInput('');
  const { state: password, bindings: passwordBindings } = useInput('');
  const [loading, setLoading] = useState(false);
  const disabled = !username || !password;
  const onSubmit = async () => {
    setLoading(true);
    const res = await login({ username, password });
    setLoading(false);

    if (res.error) {
      setError(res.error);
    } else {
      router.push('/');
    }
  };

  return (
    <Layout header={false} footer={false}>
      <div className="main">
        <div className="logo">
          <svg height="48" viewBox="0 0 75 65" fill={theme.palette.foreground}>
            <path d="M37.59.25l36.95 64H.64l36.95-64z" />
          </svg>
        </div>
        <Text h1 style={{ margin: 0, fontWeight: 300 }}>Sign in to Fedlearner</Text>
        <div className="form">
          <Input icon={<UserIcon />} placeholder="Username" width="100%" {...usernameBindings} />
          <Spacer y={0.5} />
          <Input.Password placeholder="Password" width="100%" {...passwordBindings} />
          <Spacer y={0.5} />
          <Button
            auto
            type="secondary"
            style={{ width: '100%', textTransform: 'inherit' }}
            disabled={disabled}
            loading={loading}
            onClick={onSubmit}
          >Sign in</Button>
          {error && (
            <>
              <Spacer y={0.5} />
              <Note type="error" label="error">{error}</Note>
            </>
          )}
        </div>
      </div>

      <style jsx>{styles}</style>
    </Layout>
  );
}
