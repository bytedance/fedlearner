import React, { useState, useCallback, useMemo } from 'react';
import { Table, Button, Card, Text, Link } from '@zeit-ui/react';
import useSWR from 'swr';
import produce from 'immer'
import Layout from './Layout';
import Form from './Form';
import { fetcher } from '../libs/http';
import { createTicket, updateTicket } from '../services/ticket';
import {
  DATASOURCE_TICKET_REPLICA_TYPE,
  DATASOURCE_TICKET_PARAMS
} from '../constants/form-default'
import { getParsedValueFromData, fillJSON, getValueFromJson } from '../utils/form_utils';
import { JOB_TYPE } from '../constants/job'

function fillField(data, field, editing) {
  if (data === undefined && !editing) return field
  let v = getValueFromJson(data, field.path || field.key)
  if (typeof v === 'object') {
    v = JSON.stringify(v, null, 2)
  }

  field.value = v
  field.editing = true

  return field
}

/**
 * editing: always write value to field
 * init: this call is for init form value and will not pass any group
 */
function mapValueToFields({data, fields, targetGroup, type = 'form', editing = false, init = false}) {
  return produce(fields, draft => {
    draft.map((x) => {
      x.value = data[x.key] || x.emptyDefault || ''

      if (x.groupName) {
        editing && (init = true)
        if (!init && x.groupName !== targetGroup) return
        if (x.formTypes) {
          let types = init ? x.formTypes : [type]
          types.forEach(el => {
            x.fields[el].forEach(field => fillField(data[x.groupName], field, editing))
          })
        } else {
          x.fields.forEach(field => fillField(data[x.groupName], field, editing))
        }
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

export default function TicketList({
  datasoure,
  trainning,
  filter,
  ...props
}) {

  let TICKET_REPLICA_TYPE, TICKET_PARAMS, FILTER_TYPE, PAGE_NAME
  if (datasoure) {

    PAGE_NAME = 'datasource'

    TICKET_REPLICA_TYPE = DATASOURCE_TICKET_REPLICA_TYPE

    TICKET_PARAMS = DATASOURCE_TICKET_PARAMS

    FILTER_TYPE = JOB_TYPE.datasource

  } else {

    PAGE_NAME = 'trainning'

    TICKET_REPLICA_TYPE = DATASOURCE_TICKET_REPLICA_TYPE

    TICKET_PARAMS = DATASOURCE_TICKET_PARAMS

    FILTER_TYPE = JOB_TYPE.trainning

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

  // form meta convert functions
  const rewriteFields = useCallback((draft, data) => {
    // this function will be call inner immer
  }, [])
  const mapFormMeta2Json = useCallback(() => {
    let data = {}
    fields.map((x) => {
      if (x.groupName) {
        data[x.groupName] = { [x.groupName]: formMeta[x.groupName] }
      } else {
        data[x.key] = formMeta[x.key]
      }
    })
    return data
  }, [])
  const mapFormMeta2Form = useCallback(() => {
    let data = {}
    fields.map((x) => {
      if (x.groupName) {
        data[x.groupName] = formMeta[x.groupName]
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

          for (let field of PUBLIC_PARAMS_FIELDS) {
            let value = getParsedValueFromData(data[groupName], field)
            handleParamData(draft[groupName], value, field)
          }

        } else {
          draft[x.key] = getParsedValueFromData(data, x) || draft[x.key]
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
          data: mapFormMeta2Json(paramsType),
          fields: fields.filter(el => el.groupName === paramsType),
          targetGroup: paramsType,
          type: 'json'
        })
      }
      if (targetType === 'form') {
        writeJson2FormMeta(paramsType, data)
        newFields = mapValueToFields({
          data: mapFormMeta2Form(paramsType),
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

  const PUBLIC_PARAMS_FIELDS = useMemo(() => TICKET_REPLICA_TYPE.reduce(
    (total, replicaType) => {
      const replicaKey = key => `${replicaType}.${key}`

      total.push(...[
        { key: replicaType, type: 'label' },
        {
          key: replicaKey('pair'),
          label: 'pair',
          type: 'bool-select',
          path: `spec.flReplicaSpecs.${replicaType}.pair`,
          default: TICKET_PARAMS[replicaType].pair,
        },
        {
          key: replicaKey('env'),
          label: 'env',
          type: 'name-value',
          path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].env`,
          emptyDefault: [],
          default: TICKET_PARAMS[replicaType].env,
          props: {
            ignoreKeys: ['PARTITION_NUM']
          },
          span: 24,
        },
        {
          key: replicaKey('command'),
          label: 'command',
          type: 'json',
          path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].command`,
          emptyDefault: [],
          default: TICKET_PARAMS[replicaType].command,
          span: 24,
        },
        {
          key: replicaKey('args'),
          label: 'args',
          type: 'json',
          path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].args`,
          default: TICKET_PARAMS[replicaType].args,
          emptyDefault: [],
          span: 24,
        }
      ])
      return total
    },
    []
  ), [])

  const DEFAULT_FIELDS = [
    { key: 'name', required: true },
    { key: 'federation_id', type: 'federation', label: 'federation', required: true },
    {
      key: 'job_type',
      type: 'jobType',
      props: {type: PAGE_NAME},
      required: true,
    },
    { key: 'role', type: 'jobRole', required: true },
    { key: 'expire_time' },
    {
      key: 'image',
      required: true,
      path: 'spec.flReplicaSpecs.[replicaType].template.spec.containers[].image',
      props: { width: '100%' }
    },
    {
      key: 'raw_data',
      type: 'rawData',
      higherUpdateForm: updateFormHook =>
        value => updateFormHook('num partitions', value),
    },
    {
      key: 'num partitions',
      path: {
        Master: 'spec.flReplicaSpecs.Master.template.spec.containers[].env[-1].PARTITION_NUM'
      }
    },
    { key: 'remark', type: 'text', span: 24 },
    {
      groupName: 'public_params',
      initialVisible: false,
      onFormTypeChange: formTypeChangeHandler('public_params'),
      formTypes: ['form', 'json'],
      fields: {
        form: PUBLIC_PARAMS_FIELDS,
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
  ]
  const [formVisible, setFormVisible] = useState(false);
  const [fields, setFields] = useState(DEFAULT_FIELDS);
  const [currentTicket, setCurrentTicket] = useState(null);
  const title = currentTicket ? `Edit Ticket: ${currentTicket.name}` : 'Create Ticket';
  const closeForm = () => {
    setFormMeta({})
    setFormVisible(!formVisible)
  };
  const onCreate = () => {
    setFields(mapValueToFields({data: formMeta, fields: DEFAULT_FIELDS, init: true}))
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
    setFields(mapValueToFields({data: ticket, fields: DEFAULT_FIELDS, editing: true}));
    setFormVisible(true);
  };
  const handleSubmit = (value, formTypes) => {
    const writer = formTypes['public_params'] === 'json'
      ? writeJson2FormMeta : writeForm2FormMeta
    writer('public_params', value)

    writeJson2FormMeta('private_params', value)

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