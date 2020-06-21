import React, { useState } from 'react';
import css from 'styled-jsx/css';
import { Avatar, Button, Card, Text, Grid, Input, Spacer, useTheme } from '@zeit-ui/react';
import LinkIcon from '@zeit-ui/react-icons/link';
import MailIcon from '@zeit-ui/react-icons/mail';
import useSWR from 'swr';
import Form from './Form';
import { fetcher } from '../libs/http';

// split into common styles
function useStyles(theme) {
  return css`
    .heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: ${theme.layout.pageMargin};
    }
  `;
}

function useFederationItemStyles() {
  return css`
    .heading {
      display: flex;
    }

    .title {
      margin-left: 10px;
    }

    .description {
      margin-left: 10px;
      word-break: break-all;
    }
  `;
}

function FederationItem({ data }) {
  const { id, avatar, domain, email, name, trademark, cipher, token } = data;
  const styles = useFederationItemStyles();
  return (
    <Card shadow>
      <div className="heading">
        <Avatar src={avatar} size="large" />
        <div className="title">
          <Text h3 style={{ marginBottom: '10px' }}>#{id} {trademark}</Text>
          <Text p type="secondary" style={{ margin: 0 }}>@{name}</Text>
        </div>
      </div>
      <div className="content">
        <Text p size={14} type="secondary">
          <LinkIcon size={14} />
          <span className="description">{domain}</span>
        </Text>
        <Text p size={14} type="secondary">
          <MailIcon size={14} />
          <span className="description">{email}</span>
        </Text>
        <div>
          <Text p size={14} type="secondary">Cipher:</Text>
          {cipher
            ? <Input.Password value={cipher} readOnly className="passwordViwer" />
            : 'None'}
        </div>
        <div>
          <Text p size={14} type="secondary">Token:</Text>
          {token
            ? <Input.Password value={token} readOnly className="passwordViwer" />
            : 'None'}
        </div>
      </div>

      <style jsx>{styles}</style>
    </Card>
  );
}

export default function FederationList() {
  const theme = useTheme();
  const styles = useStyles(theme);
  const { data } = useSWR('federations', fetcher);
  const federations = data ? data.data : null;
  const [formVisible, setFormVisible] = useState(false);

  if (formVisible) {
    return <Form title="Create Federation" onCancel={() => setFormVisible(false)} />;
  }

  return (
    <>
      <div className="heading">
        <Text h2>Federations</Text>
        <Button auto type="secondary" onClick={() => setFormVisible(true)}>Create Federation</Button>
      </div>
      <Grid.Container gap={2}>
        {federations && federations.map((x) => (
          <Grid key={x.id} xs={24} sm={12} md={8} lg={6} xl={6}>
            <FederationItem data={x} />
          </Grid>
        ))}
      </Grid.Container>
      <Spacer y={2} />

      <style jsx>{styles}</style>
    </>
  );
}
