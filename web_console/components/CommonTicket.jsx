import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { Table, Button, Card, Text, Link, Tooltip } from '@zeit-ui/react';
import AlertCircle from '@geist-ui/react-icons/alertCircle'
import useSWR from 'swr';
import produce from 'immer'
import Layout from './Layout';
import Form from './Form';
import { fetcher } from '../libs/http';
import { createTicket, updateTicket } from '../services/ticket';
import {
  TICKET_DATA_JOIN_PARAMS,
  TICKET_NN_PARAMS,
  TICKET_PSI_DATA_JOIN_PARAMS,
  TICKET_TREE_PARAMS,
  TICKET_DATA_JOIN_REPLICA_TYPE,
  TICKET_NN_REPLICA_TYPE,
  TICKET_PSI_DATA_JOIN_REPLICA_TYPE,
  TICKET_TREE_REPLICA_TYPE
} from '../constants/form-default'
import { getParsedValueFromData, fillJSON, getValueFromJson, filterArrayValue, getValueFromEnv } from '../utils/form_utils';
import { JOB_TYPE_CLASS, JOB_TYPE } from '../constants/job'

const ENV_PATH = 'spec.flReplicaSpecs.[replicaType].template.spec.containers[].env'
const PARAMS_GROUP = ['public_params', 'private_params']

function fillField(data, field, editing) {
  if (data === undefined && !editing) return field

  let isSetValueWithEmpty = false
  let disabled = false

  let v = getValueFromJson(data, field.path || field.key)

  const envPath = ENV_PATH.replace('[replicaType]', 'Master')

  if (field.key === 'raw_data') {
    v = getValueFromEnv(data['public_params'], envPath,'RAW_DATA_SUB_DIR')
      || getValueFromEnv(data['private_params'], envPath,'RAW_DATA_SUB_DIR')
    v = v.replace('portal_publish_dir/', '')
  }
  else if (field.key === 'name' && editing) {
    disabled = true
  }
  else if (field.key === 'federation_id') {
    const federationID = parseInt(localStorage.getItem('federationID'))
    if (federationID > 0) {
      v = federationID
      disabled = true
    }
  }
  else if (field.key === 'num_partitions') {
    v = getValueFromEnv(data['public_params'], envPath, 'PARTITION_NUM')
      || getValueFromEnv(data['private_params'], envPath, 'PARTITION_NUM')
  }
  else if (field.key === 'image') {
    v = getValueFromJson(data['public_params'] || {}, field.path.replace('[replicaType]', 'Master'))
      || getValueFromJson(data['private_params'] || {}, field.path.replace('[replicaType]', 'Master'))
  }
  else if (field.type === 'bool-select') {
    v = typeof v === 'boolean' ? v : true
  }
  else if (field.key === 'datasource') {
    v = getValueFromEnv(data['public_params'], envPath, 'DATA_SOURCE')
      || getValueFromEnv(data['private_params'], envPath, 'DATA_SOURCE')
  }
  else if (field.key === 'code_key') {
    v = getValueFromEnv(data['public_params'], ENV_PATH.replace('[replicaType]', 'Worker'), 'CODE_KEY')
      || getValueFromEnv(data['private_params'], ENV_PATH.replace('[replicaType]', 'Worker'), 'CODE_KEY')
  }
  else {
    v = v || field.emptyDefault || ''
  }

  if (typeof v === 'object') {
    v = JSON.stringify(v, null, 2)
  }

  if (v !== undefined || (v === undefined && isSetValueWithEmpty)) {
    field.value = v
  }
  field.editing = true

  if (!field.props) field.props = {}
  field.props.disabled = disabled

  return field
}

/**
 * editing: always write value to field
 * init: this call is for init form value and will not pass any group
 */
function mapValueToFields({data, fields, targetGroup, type = 'form', editing = false, init = false}) {
  return produce(fields, draft => {
    draft.map((x) => {
      if (x.groupName) {
        editing && (init = true)
        if (!data[x.groupName]) return
        if (!init && x.groupName !== targetGroup) return
        if (x.formTypes) {
          let types = init ? x.formTypes : [type]
          types.forEach(el => {
            x.fields[el].forEach(field => fillField(data[x.groupName], field, editing))
          })
        } else {
          x.fields.forEach(field => {
            fillField(data[x.groupName], field, editing)
          })
        }
      } else {
        fillField(data, x, editing)
      }
    });
  })
}

function handleParamData(container, data, field) {
  if (field.type === 'label') { return }

  let path = field.path || field.key
  let value = data

  fillJSON(container, path, value)
}

let formMeta = {}
const setFormMeta = data => formMeta = data

let jobType = ''

export default function TicketList({
  datasoure,
  training,
  filter,
  ...props
}) {

  let TICKET_REPLICA_TYPE, INIT_PARAMS, FILTER_TYPE, PAGE_NAME, DEFAULT_JOB_TYPE
  if (datasoure) {

    PAGE_NAME = 'datasource'

    TICKET_REPLICA_TYPE = TICKET_DATA_JOIN_REPLICA_TYPE

    INIT_PARAMS = TICKET_DATA_JOIN_PARAMS

    FILTER_TYPE = JOB_TYPE_CLASS.datasource

    DEFAULT_JOB_TYPE = JOB_TYPE.data_join

  } else {

    PAGE_NAME = 'training'

    TICKET_REPLICA_TYPE = TICKET_NN_REPLICA_TYPE

    INIT_PARAMS = TICKET_NN_PARAMS

    FILTER_TYPE = JOB_TYPE_CLASS.training

    DEFAULT_JOB_TYPE = JOB_TYPE.nn_model

  }

  filter = filter
    || useCallback(job => FILTER_TYPE.some(type => type === job.job_type), [])

  const { data, mutate } = useSWR('tickets', fetcher);
  const tickets = data ? data.data.filter(filter) : null;
  const columns = tickets && tickets.length > 0
    ? [
      ...Object.keys(tickets[0]).filter((x) => !['public_params', 'private_params', 'expire_time', 'created_at', 'updated_at', 'deleted_at'].includes(x)),
      'operation',
    ]
    : [];

  // rewrite functions
  const rewriteEnvs = useCallback((draft, data, rules) => {
    PARAMS_GROUP.forEach(paramType => {
      TICKET_REPLICA_TYPE.forEach(replicaType => {
        let envPath = ENV_PATH.replace('[replicaType]', replicaType)

        if (!draft[paramType]) {
          draft[paramType] = {}
        }

        let envs = getValueFromJson(draft[paramType], envPath)
        if (!envs) { envs = [] }

        let envNames = envs.map(env => env.name)
        rules.forEach(el => {
          if (el.writeTo && !el.writeTo.some(x => x === replicaType)) return

          let idx = envNames.indexOf(el.name)
          let value = el.getValue(data) || ''
          if (idx >= 0) {
            envs[idx].value = value.toString()
          } else {
            // here envs is not extensible, push will throw error
            envs = envs.concat({name: el.name, value: value.toString()})
          }
        })
        // trigger immer‘s intercepter
        fillJSON(draft[paramType], envPath, envs)
      })
    })
  }, [])
  const commonRewrite = useCallback((draft, data) => {
    TICKET_REPLICA_TYPE.forEach(replicaType => {
      let path = `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].image`

      PARAMS_GROUP.forEach(paramType => {
        if (!draft[paramType]) {
          draft[paramType] = {}
        }
        fillJSON(draft[paramType], path, data.image)
      })
    })

    // image
    draft.image && delete draft.image
  }, [])
  const dataSourceRewrite = useCallback((draft, data) => {
    // envs
    const insert2Env = [
      { name: 'RAW_DATA_SUB_DIR', getValue: data => 'portal_publish_dir/' + (data.raw_data.name || data.raw_data) },
      { name: 'PARTITION_NUM', getValue: data => data.num_partitions },
    ]
    rewriteEnvs(draft, data, insert2Env)

    // replicas
    TICKET_REPLICA_TYPE.forEach(replicaType => {
      let num = replicaType === 'Master' ? 1 : draft.num_partitions

      PARAMS_GROUP.forEach(paramType => {
        fillJSON(draft[paramType], `spec.flReplicaSpecs.${replicaType}.replicas`, parseInt(num))
      })
    })

    // delete fields
    draft.raw_data && delete draft.raw_data
    draft.num_partitions && delete draft.num_partitions

  }, [])
  const trainingRewrite = useCallback((draft, data) => {
    // envs
    const insert2Env = [
      { name: 'DATA_SOURCE', getValue: data => data.datasource },
      { name: 'CODE_KEY', getValue: data => data.code_key, writeTo: ['Worker'] },
    ]
    rewriteEnvs(draft, data, insert2Env)

    // delete fields
    draft.datasource && delete draft.datasource
    draft.code_key && delete draft.code_key

  }, [])
  const rewriteFields = useCallback((draft, data) => {
    // this function will be call inner immer
    commonRewrite(draft, data)
    if (datasoure) {
      dataSourceRewrite(draft, data)
    }
    if (training) {
      trainingRewrite(draft, data)
    }
  }, [])
  // ---end---
  // form meta convert functions
  const mapFormMeta2FullData = useCallback((fields = fields) => {
    let data = {}
    fields.map((x) => {
      if (x.groupName) {
        data[x.groupName] = { ...formMeta[x.groupName] }
        data[x.groupName][x.groupName] = formMeta[x.groupName]
      } else {
        data[x.key] = formMeta[x.key]
      }
    })
    return data
  }, [])
  const writeJson2FormMeta = useCallback((groupName, data) => {
    setFormMeta(produce(formMeta, draft => {
      fields.map((x) => {
        if (x.groupName === groupName) {
          draft[groupName] = JSON.parse(data[groupName][groupName] || x.emptyDefault || '{}')
        } else {
          draft[x.key] = getParsedValueFromData(data, x) || draft[x.key]
        }
      })

      rewriteFields(draft, data)
    }))
  }, [])
  const writeForm2FormMeta = useCallback((groupName, data) => {
    setFormMeta(produce(formMeta, draft => {
      fields.map(x => {
        if (x.groupName === groupName) {
          if (!draft[groupName]) { draft[groupName] = {} }

          for (let field of getPublicParamsFields()) {
            let value = getParsedValueFromData(data[groupName], field)
            handleParamData(draft[groupName], value, field)
          }

        } else {
          draft[x.key] = getParsedValueFromData(data, x)
        }
      })
      rewriteFields(draft, data)
    }))
  }, [])
  const formTypeChangeHandler = paramsType => (data, currType, targetType) => {
    let newFields
    try {
      if (targetType === 'json') {
        writeForm2FormMeta(paramsType, data)
        newFields = mapValueToFields({
          data: mapFormMeta2FullData(fields),
          fields: fields.filter(el => el.groupName === paramsType),
          targetGroup: paramsType,
          type: 'json'
        })
      }
      if (targetType === 'form') {
        writeJson2FormMeta(paramsType, data)
        newFields = mapValueToFields({
          data: mapFormMeta2FullData(fields),
          fields: fields.filter(el => el.groupName === paramsType),
          targetGroup: paramsType,
          type: 'form'
        })
      }
    } catch (error) {
      return { error }
    }
    return { newFields }
  }
  // --end---

  const onJobTypeChange = useCallback((value, totalData, groupFormType) => {
    jobType = value
    writeFormMeta(totalData,groupFormType)

    switch (value) {
      case JOB_TYPE.data_join:
        TICKET_REPLICA_TYPE = TICKET_DATA_JOIN_REPLICA_TYPE
        setFormMeta({...formMeta, ...TICKET_DATA_JOIN_PARAMS}); break
      case JOB_TYPE.psi_data_join:
        TICKET_REPLICA_TYPE = TICKET_PSI_DATA_JOIN_REPLICA_TYPE
        setFormMeta({...formMeta, ...TICKET_PSI_DATA_JOIN_PARAMS}); break
      case JOB_TYPE.nn_model:
        TICKET_REPLICA_TYPE = TICKET_NN_REPLICA_TYPE
        setFormMeta({...formMeta, ...TICKET_NN_PARAMS}); break
      case JOB_TYPE.tree_model:
        TICKET_REPLICA_TYPE = TICKET_TREE_REPLICA_TYPE
        setFormMeta({...formMeta, ...TICKET_TREE_PARAMS}); break
    }

    setFields(
      mapValueToFields({
        data: mapFormMeta2FullData(fields),
        fields: getDefauktFields(),
        init: true,
      })
    )
  }, [])

  const getPublicParamsFields = useCallback(() => TICKET_REPLICA_TYPE.reduce(
    (total, replicaType) => {
      const replicaKey = key => `${replicaType}.${key}`

      total.push(...[
        { key: replicaType, type: 'label' },
        {
          key: replicaKey('pair'),
          label: 'pair',
          type: 'bool-select',
          path: `spec.flReplicaSpecs.${replicaType}.pair`,
        },
        {
          key: replicaKey('env'),
          label: 'env',
          type: 'name-value',
          path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].env`,
          emptyDefault: [],
          // props: {
          //   ignoreKeys: ['PARTITION_NUM', 'CODE_KEY']
          // },
          span: 24,
        },
        {
          key: replicaKey('command'),
          label: 'command',
          type: 'json',
          path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].command`,
          emptyDefault: [],
          span: 24,
        },
        {
          key: replicaKey('args'),
          label: 'args',
          type: 'json',
          path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].args`,
          emptyDefault: [],
          span: 24,
        }
      ])
      return total
    },
    []
  ), [TICKET_REPLICA_TYPE])

  const getDefauktFields = useCallback(() => filterArrayValue([
    { key: 'name', required: true },
    { key: 'federation_id', type: 'federation', label: 'federation', required: true },
    {
      key: 'job_type',
      type: 'jobType',
      label: (
        <>
          <span style={{paddingRight: '4px'}}>job_type</span>
          <Tooltip style={{color: '#444'}} text={<span className="formItemLabel">change job type will reset all params</span>}>
            <span style={{position: 'relative', top: '4px'}}><AlertCircle size={16}/></span>
          </Tooltip>
        </>
      ),
      props: {type: PAGE_NAME},
      required: true,
      default: DEFAULT_JOB_TYPE,
      onChange: onJobTypeChange,
    },
    { key: 'role', type: 'jobRole', required: true },
    { key: 'expire_time' },
    {
      key: 'image',
      required: true,
      path: 'spec.flReplicaSpecs.[replicaType].template.spec.containers[].image',
      props: { width: '100%' }
    },
    datasoure && {
      key: 'raw_data',
      type: 'rawData',
      callback: updateForm =>
        value => updateForm('num_partitions', value?.output_partition_num),
    },
    datasoure && {
      key: 'num_partitions',
      label: 'num partitions',
    },
    training && {
      key: 'datasource',
      type: 'datasource',
      required: true,
    },
    (training && jobType === JOB_TYPE.nn_model) ? {
      key: 'code_key',
      props: { width: '100%' }
    } : undefined,
    { key: 'remark', type: 'text', span: 24 },
    {
      groupName: 'public_params',
      initialVisible: false,
      onFormTypeChange: formTypeChangeHandler('public_params'),
      formTypes: ['form', 'json'],
      fields: {
        form: getPublicParamsFields(),
        json: [
          {
            key: 'public_params',
            type: 'json',
            span: 24,
            hideLabel: true,
            props: {
              minHeight: '500px'
            },
          },
        ]
      }
    },
    {
      groupName: 'private_params',
      initialVisible: false,
      fields: [
        {
          key: 'private_params',
          type: 'json',
          span: 24,
          hideLabel: true,
          emptyDefault: {},
          props: {
            minHeight: '500px'
          },
        },
      ]
    }
  ]), [TICKET_REPLICA_TYPE, training, datasoure, jobType])
  const [formVisible, setFormVisible] = useState(false);
  const [fields, setFields] = useState(getDefauktFields());
  const [currentTicket, setCurrentTicket] = useState(null);
  const title = currentTicket ? `Edit Ticket: ${currentTicket.name}` : 'Create Ticket';
  const closeForm = () => {
    setCurrentTicket(null)
    setFormMeta({})
    setFormVisible(!formVisible)
  };
  const onCreate = () => {
    setFormMeta({ ...INIT_PARAMS })
    setFields(mapValueToFields({data: formMeta, fields: getDefauktFields(), init: true}))
    setFormVisible(true);
  }
  const onOk = (ticket) => {
    mutate({
      data: [...tickets, ticket],
    });
    closeForm();
  };
  const handleEdit = (ticket) => {
    setCurrentTicket(ticket);
    setFormMeta(ticket)

    jobType = ticket.job_type

    setFields(mapValueToFields({data: ticket, fields: getDefauktFields(), editing: true}));
    setFormVisible(true);
  };

  const writeFormMeta = (data, formTypes) => {
    const writer = formTypes['public_params'] === 'json'
      ? writeJson2FormMeta : writeForm2FormMeta
    writer('public_params', data)

    writeJson2FormMeta('private_params', data)
  }
  const handleSubmit = (data, formTypes) => {
    writeFormMeta(data, formTypes)

    if (currentTicket) {
      return updateTicket(currentTicket.id, formMeta);
    }

    return createTicket(formMeta);
  };
  const operation = (actions, rowData) => {
    const onHandleEdit = (e) => {
      e.preventDefault();
      handleEdit(rowData.rowValue);
    };
    return <Link href="#" color onClick={onHandleEdit}>Edit</Link>;
  };
  const dataSource = tickets
    ? tickets.map((x) => ({ ...x, operation }))
    : [];

  return (
    <Layout>
      {formVisible
        ? (
          <Form
            title={title}
            fields={fields}
            onSubmit={handleSubmit}
            onOk={onOk}
            onCancel={closeForm}
          />
        )
        : (
          <>
            <div className="heading">
              <Text h2>Tickets</Text>
              <Button auto type="secondary" onClick={onCreate}>Create Ticket</Button>
            </div>
            {tickets && (
              <Card>
                <Table data={dataSource}>
                  {columns.map((x) => <Table.Column key={x} prop={x} label={x} />)}
                </Table>
              </Card>
            )}
          </>
        )}
    </Layout>
  );
}