import React, { useState } from 'react';
import css from 'styled-jsx/css';
import { Avatar, Button, Card, Code, Text, Grid, Popover, Link } from '@zeit-ui/react';
import PhoneIcon from '@zeit-ui/react-icons/phone';
import MailIcon from '@zeit-ui/react-icons/mail';
import InfoIcon from '@zeit-ui/react-icons/info';
import useSWR from 'swr';
import Layout from '../../components/Layout';
import Form from '../../components/Form';
import { fetcher } from '../../libs/http';
import { createFederation, updateFederation } from '../../services';

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

function FederationItem({ data, onEdit }) {
  const { id, avatar, tel, email, name, trademark, k8s_settings } = data;
  const styles = useFederationItemStyles();
  const handleEdit = (e) => {
    e.preventDefault();
    onEdit(data);
  };
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
          <PhoneIcon size={14} />
          <span className="description">{tel || 'None'}</span>
        </Text>
        <Text p size={14} type="secondary">
          <MailIcon size={14} />
          <span className="description">{email || 'None'}</span>
        </Text>
        <Text p size={14} style={{ marginBottom: 0 }} type="secondary">
          k8s_settings：
          <Popover trigger="hover" content={<Code block>{JSON.stringify(k8s_settings, null, 2)}</Code>}>
            <InfoIcon size={14} />
          </Popover>
        </Text>
      </div>

      <Card.Footer className="formCardFooter">
        <Link href="#" color onClick={handleEdit}>Edit</Link>
      </Card.Footer>

      <style jsx>{styles}</style>
    </Card>
  );
}

const DEFAULT_FIELDS = [
  { key: 'name', required: true },
  { key: 'trademark', span: 12 },
  { key: 'email' },
  { key: 'tel', label: 'telephone' },
  { key: 'avatar' },
  {
    key: 'k8s_settings',
    type: 'json',
    required: true,
    span: 24,
    props: {
      minHeight: '300px',
    },
  },
];

function mapValueToFields(federation, fields) {
  return fields.map((x) => {
    const field = { ...x, value: federation[x.key] };

    if (x.key === 'name') {
      field.props = {
        disabled: true,
      };
    }

    if (x.key === 'k8s_settings') {
      field.value = JSON.stringify(field.value, null, 2);
    }

    return field;
  });
}

export default function FederationList() {
  const { data, mutate } = useSWR('federations', fetcher);
  const federations = data ? data.data : null;
  const [formVisible, setFormVisible] = useState(false);
  const [fields, setFields] = useState(DEFAULT_FIELDS);
  const [currentFederation, setCurrentFederation] = useState(null);
  const title = currentFederation ? `Edit Federation: ${currentFederation.name}` : 'Create Federation';
  const toggleForm = () => {
    setFormVisible(!formVisible);
    setCurrentFederation(null);
    setFields(DEFAULT_FIELDS);
  };
  const onOk = (federation) => {
    mutate({
      data: [...federations, federation],
    });
    toggleForm();
  };
  const handleEdit = (federation) => {
    setCurrentFederation(federation);
    setFields(mapValueToFields(federation, fields));
    setFormVisible(true);
  };
  const handleSubmit = (value) => {
    const json = {
      ...value,
      k8s_settings: JSON.parse(value.k8s_settings),
    };

    if (currentFederation) {
      return updateFederation(currentFederation.id, json);
    }

    return createFederation(json);
  };

  return (
    <Layout>
      {formVisible
        ? (
          <Form
            title={title}
            fields={fields}
            onSubmit={handleSubmit}
            onOk={onOk}
            onCancel={toggleForm}
          />
        )
        : (
          <>
            <div className="heading">
              <Text h2>Federations</Text>
              <Button auto type="secondary" onClick={() => setFormVisible(true)}>Create Federation</Button>
            </div>
            <Grid.Container gap={2}>
              {federations && federations.map((x) => (
                <Grid key={x.id} xs={24} sm={12} md={8} lg={6} xl={6}>
                  <FederationItem data={x} onEdit={handleEdit} />
                </Grid>
              ))}
            </Grid.Container>
          </>
        )}
    </Layout>
  );
}
