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
import produce from 'immer'

import { K8S_SETTINGS } from '../../constants/form-default'

const fillJSON = (container, path, value) => {
  if (typeof path === 'string') {
    path = path.split('.')
  }
  if (path.length === 1) {
    container[path[0]]= value
    return
  }
  if (container[path[0]] === undefined) {
    container[path[0]] = {}
  }
  let c = container[path[0]]
  fillJSON(c, path.slice(1), value)
}

const getValueFromJson = (data, path) => {
  if (typeof path === 'string') {
    path = path.split('.')
  }
  if (path.length === 1) {
    return data[path[0]]
  }
  if (data[path[0]] === undefined) return undefined
  return getValueFromJson(data[path[0]], path.slice(1))
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

const switchK8sSettingsFormType = (data, currType, targetType) => {
  if (targetType === 'json') {
    const k8s_settings = {}
    for (let field of K8S_SETTINGS_FIELDS) {
      let fieldValue = data[field.key]
      if (['json', 'name-value'].some(el => el === field.type)) {
        try {
          fieldValue = JSON.parse(
            fieldValue || (field.type === 'name-value' ? '[]' : '{}')
          )
        } catch {
          return {error: `Error occurred when parsing json. Please check ${field.key}`}
        }
      }
      fillJSON(k8s_settings, field.path || [field.key], fieldValue)
    }
    // x-federation
    data['x-federation']
      && fillJSON(k8s_settings, 'grpc_spec.extraHeaders.x-federation', data['x-federation'])

    return { k8s_data: JSON.stringify(k8s_settings, null, 2) }
  }
  if (targetType === 'form') {
    const formData = {}
    let value
    try {
      value = JSON.parse(data['k8s_data'])
    } catch (e) {
      return {error: 'Error occurred when parsing json. Please check.'}
    }

    for (let field of K8S_SETTINGS_FIELDS) {
      let fieldValue = getValueFromJson(value, field.path || [field.key])
      if (['json', 'name-value'].some(el => el === field.type)) {
        fieldValue = JSON.stringify(fieldValue, null, 2)
      }
      formData[field.key] = fieldValue
    }
    formData['x-federation'] = getValueFromJson(value, 'grpc_spec.extraHeaders.x-federation')

    return formData
  }
}

const K8S_SETTINGS_FIELDS = [
  { key: 'storage_root_path', default: K8S_SETTINGS.storage_root_path },
  {
    key: 'imagePullSecrets',
    default: K8S_SETTINGS.imagePullSecrets,
    type: 'json',
    span: 24,
    path: 'global_replica_spec.template.spec.imagePullSecrets'
  },
  {
    key: 'env',
    type: 'name-value',
    span: 24,
    default: K8S_SETTINGS.env,
    props: {
      minHeight: '150px',
    },
    path: 'global_replica_spec.template.spec.containers.envs'
  },
  {
    key: 'grpc_spec',
    type: 'json',
    span: 24,
    default: K8S_SETTINGS.grpc_spec,
    props: {
      minHeight: '150px',
    },
  },
  {
    key: 'leader_peer_spec',
    type: 'json',
    span: 24,
    default: K8S_SETTINGS.leader_peer_spec,
    props: {
      minHeight: '150px',
    },
  },
  {
    key: 'follower_peer_spec',
    type: 'json',
    span: 24,
    default: K8S_SETTINGS.follower_peer_spec,
    props: {
      minHeight: '150px',
    },
  },
]

const DEFAULT_FIELDS = [
  { key: 'name', required: true },
  { key: 'trademark' },
  { key: 'x-federation' },
  { key: 'email' },
  { key: 'tel', label: 'telephone' },
  { key: 'avatar' },
  {
    groupName: 'k8s_settings',
    formTypes: ['form', 'json'],
    onFormTypeChange: switchK8sSettingsFormType,
    fields: {
      form: K8S_SETTINGS_FIELDS,
      json: [
        {
          key: 'k8s_data',
          type: 'json',
          hideLabel: true,
          span: 24,
          props: {
            minHeight: '500px'
          }
        }
      ]
    },
  },
];

/**
 * set init value and props of fields
 */
function fillField(data, field) {
  let v = getValueFromJson(data, field.path || field.key)
  if (typeof v === 'object') {
    v = JSON.stringify(v, null, 2)
  }
  field.value = v
  field.editing = true

  if (field.key === 'name') {
    field.props = {
      disabled: true,
    };
  }
  if (field.key === 'x-federation') {
    let xFederation = getValueFromJson(data, 'k8s_settings.grpc_spec.extraHeaders.x-federation')
    xFederation && (field.value = xFederation)
  }

  return field
}

function mapValueToFields(federation, fields) {
  return produce(fields, draft => {
    draft.map((x) => {
      if (x.groupName === 'k8s_settings') {
        x.fields['form'].map(item => fillField(federation['k8s_settings'], item))
      } else {
        fillField(federation, x)
      }
    })
  })
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

  const checkValue = (field, value) => {
    if (field.key === 'env' && value) {
      for (let {name, value} of value) {
        if (name === '' || value === '') {
          return 'Please fill env'
        }
      }
    }
    if (field.type === 'json') {
      try {
        JSON.parse(value)
      } catch {
        return 'json parse failed.Please check ' + field.key
      }
    }
  }

  const handleSubmit = (value, groupFormType) => {
    let k8s_settings = {}
    // gen json
    if (groupFormType['k8s_settings'] === 'json') {
      k8s_settings = JSON.parse(value.k8s_settings.k8s_data)
    } else {
      for (let field of K8S_SETTINGS_FIELDS) {
        let fieldValue = value.k8s_settings[field.key]
        let error = checkValue(field, fieldValue)
        if (error) {
          return {error}
        }
        if (['json', 'name-value'].some(t => field.type === t)) {
          fieldValue = JSON.parse(fieldValue)
        }
        fieldValue !== undefined && fillJSON(k8s_settings, field.path || [field.key], fieldValue)
      }
    }
    // x-federation
    value['x-federation']
      && fillJSON(k8s_settings, 'grpc_spec.extraHeaders.x-federation', value['x-federation'])

    const json = {
      ...value,
      k8s_settings,
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
