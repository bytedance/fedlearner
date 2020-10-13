import React, { useState, useMemo } from 'react';
import css from 'styled-jsx/css';
import { Avatar, Button, Card, Code, Text, Grid, Popover, Link, Spacer } from '@zeit-ui/react';
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
import { fillJSON, getValueFromJson, getParsedValueFromData } from '../../utils/form_utils'
import { federationHeartbeat } from '../../services/index'

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

const Status = {
  unknown: 'unknown',
  success: 'success',
  error: 'error',
}

const StatusColor = {
  success: 'limegreen',
  error: 'red',
}

function FederationItem({ data, onEdit }) {
  const { id, avatar, tel, email, name, trademark, k8s_settings } = data;
  const styles = useFederationItemStyles();
  const handleEdit = (e) => {
    e.preventDefault();
    onEdit(data);
  };

  const [checking, setChecking] = useState(false)
  const [connStatus, setConnStatus] = useState(Status.unknown)
  const checkConn = () => {
    setChecking(true)
    federationHeartbeat(id).then(res => {
      if (res.status === Status.success) {
        setConnStatus(Status.success)
      } else {
        setConnStatus(Status.error)
      }
      setChecking(false)
    })
  }

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
        <Text p size={14} type="secondary">
          k8s_settings：
          <Popover trigger="hover" content={<Code block>{JSON.stringify(k8s_settings, null, 2)}</Code>}>
            <InfoIcon size={14} />
          </Popover>
        </Text>
        <Text p size={14} style={{ marginBottom: 0 }} type="secondary">
          connection status：
          <span style={{color: StatusColor[connStatus]}}>{connStatus}</span>
        </Text>
      </div>

      <Card.Footer className="formCardFooter" disableAutoMargin>
        <Link href="#" color onClick={handleEdit}>Edit</Link>
        <Button
          auto
          loading={checking}
          size="small"
          style={{padding: '0 0.8rem'}}
          onClick={checkConn}
        >
          check connection
        </Button>
      </Card.Footer>

      <style jsx>{styles}</style>
    </Card>
  );
}

const K8S_SETTINGS_FIELDS = [
  { key: 'namespace', default: K8S_SETTINGS.namespace },
  { key: 'storage_root_path', default: K8S_SETTINGS.storage_root_path },
  {
    key: 'imagePullSecrets',
    type: 'json',
    span: 24,
    path: 'global_replica_spec.template.spec.imagePullSecrets',
    emptyDefault: {}
  },
  {
    key: 'env',
    type: 'name-value',
    span: 24,
    props: {
      minHeight: '150px',
    },
    path: 'global_replica_spec.template.spec.containers[].env',
    emptyDefault: []
  },
  {
    key: 'grpc_spec',
    type: 'json',
    span: 24,
    props: {
      minHeight: '150px',
    },
    emptyDefault: {}
  },
  {
    key: 'leader_peer_spec',
    type: 'json',
    span: 24,
    props: {
      minHeight: '150px',
    },
    emptyDefault: {}
  },
  {
    key: 'follower_peer_spec',
    type: 'json',
    span: 24,
    props: {
      minHeight: '150px',
    },
    emptyDefault: {}
  },
]

/**
 * set init value and props of fields
 */
function fillField(data, field, edit=false) {
  let v = getValueFromJson(data, field.path || field.key)
  if (typeof v === 'object') {
    v = JSON.stringify(v, null, 2)
  }
  field.value = v
  field.editing = true

  if (field.key === 'name') {
    field.props = {
      disabled: edit,
    };
  }
  if (field.key === 'x-federation') {
    let xFederation = getValueFromJson(data, 'k8s_settings.grpc_spec.extraHeaders.x-federation')
    xFederation && (field.value = xFederation)
  }
  return field
}

function mapValueToFields({federation, fields, type='form', edit=false}) {
  return produce(fields, draft => {
    draft.map((x) => {
      if (x.groupName === 'k8s_settings') {
        x.fields[type].map(item => fillField(federation['k8s_settings'], item, edit))
      } else {
        fillField(federation, x, edit)
      }
    })
  })
}

let formMeta = {}
function setFormMeta (value) { formMeta = value }

export default function FederationList() {
  /**
   * formMeta is the record of raw form info.
   * while formType is `form`, value of fields will read from formMeta,
   * while formType is `json`, json value will use raw data in formMeta.
   * There are two moments to update formMeta:
   * 1. switching formType
   *    formMeta needs to be update **manually** in switchCallback to make data consistency
   * 2. submitting
   *    formMeta will be post
   */
  // const [formMeta, setFormMeta] = useState({})

  const { data, mutate } = useSWR('federations', fetcher);
  const federations = data ? data.data : null;
  const [formVisible, setFormVisible] = useState(false);
  const [currentFederation, setCurrentFederation] = useState(null);
  const title = currentFederation ? `Edit Federation: ${currentFederation.name}` : 'Create Federation';

  // form meta convert functions
  const mapFormMeta2Json = () => {
    let data = {}
    fields.map((x) => {
      if (x.groupName === 'k8s_settings') {
        data.k8s_settings = { k8s_data: formMeta.k8s_settings }
      } else {
        data[x.key] = formMeta[x.key]
      }
    })
    return data
  }
  const mapFormMeta2Form = () => {
    let data = {}
    fields.map((x) => {
      if (x.groupName === 'k8s_settings') {
        data.k8s_settings = formMeta.k8s_settings
      } else {
        data[x.key] = formMeta[x.key]
      }
    })
    return data
  }
  const writeJson2FormMeta = (data) => {
    setFormMeta(produce(formMeta, draft => {
      fields.map((x) => {
        if (x.groupName === 'k8s_settings') {
          let k8s_settings = JSON.parse(data.k8s_settings['k8s_data'])
          data['x-federation']
            && fillJSON(k8s_settings, 'grpc_spec.extraHeaders.x-federation', data['x-federation'])
          draft.k8s_settings = {...draft.k8s_settings, ...k8s_settings}
        } else {
          draft[x.key] = getParsedValueFromData(data, x) || draft[x.key]
        }
      })
    }))
  }
  const writeForm2FormMeta = (data) => {
    setFormMeta(produce(formMeta, draft => {
      fields.map(x => {
        if (x.groupName === 'k8s_settings') {
          if (!draft.k8s_settings) { draft.k8s_settings = {} }
          for (let field of K8S_SETTINGS_FIELDS) {
            fillJSON(
              draft.k8s_settings, field.path || field.key,
              getParsedValueFromData(data.k8s_settings, field)
            )
          }
          data['x-federation']
            && fillJSON(draft.k8s_settings, 'grpc_spec.extraHeaders.x-federation', data['x-federation'])
        } else {
          draft[x.key] = getParsedValueFromData(data, x) || draft[x.key]
        }
      })
    }))
  }
  // --- end ---
  const switchK8sSettingsFormType = (data, currType, targetType) => {
    let newFields
    try {
      if (targetType === 'json') {
        writeForm2FormMeta(data)
        newFields = mapValueToFields({federation: mapFormMeta2Json(), fields, type: 'json'})
        setFields(newFields)
      }
      if (targetType === 'form') {
        writeJson2FormMeta(data)
        newFields = mapValueToFields({federation: mapFormMeta2Form(), fields, type: 'form'})
        setFields(newFields)
      }
    } catch (error) {
      return { error }
    }
    return { newFields }
  }
  const DEFAULT_FIELDS = useMemo(() => [
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
  ], []);
  const [fields, setFields] = useState(DEFAULT_FIELDS);

  const onClickCreate = () => {
    setFormMeta({ k8s_settings: K8S_SETTINGS })
    setFields(mapValueToFields({federation: mapFormMeta2Form(), fields}))
    setFormVisible(true)
  }
  const toggleForm = () => {
    setFormVisible(!formVisible);
    if (formVisible) {
      setFormMeta({})
    }
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
    setFormMeta(federation)
    setCurrentFederation(federation);
    setFields(mapValueToFields({federation, fields, edit: true}));
    setFormVisible(true);
  };

  /**
   * k8s setting validator
   * @param {*} field form field
   * @param {*} value field value. NOTE json is as as string
   */
  const checkK8sSetting = (field, value) => {
    if (field.key === 'env' && value) {
      value = JSON.parse(value)
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
    for (let field of K8S_SETTINGS_FIELDS) {
      let error = checkK8sSetting(field, value.k8s_settings[field.key])
      if (error) {
        return {error}
      }
    }

    const writer = groupFormType.k8s_settings === 'json'
      ? writeJson2FormMeta : writeForm2FormMeta
    writer(value)

    if (currentFederation) {
      return updateFederation(currentFederation.id, formMeta);
    }

    return createFederation(formMeta);
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
              <Button auto type="secondary" onClick={onClickCreate}>Create Federation</Button>
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
