import React, { useState, useCallback } from 'react';
import { Table, Button, Card, Text, Link } from '@zeit-ui/react';
import useSWR from 'swr';
import produce from 'immer'
import Layout from '../../../components/Layout';
import Form from '../../../components/Form';
import { fetcher } from '../../../libs/http';
import { createTicket, updateTicket } from '../../../services/ticket';
import {
  DATASOURCE_TICKET_REPLICA_TYPE,
  DATASOURCE_TICKET_PARAMS
} from '../../../constants/form-default'
import { getParsedValueFromData, fillJSON, getValueFromJson } from '../../../utils/form_utils';

const PUBLIC_PARAMS_FIELDS = DATASOURCE_TICKET_REPLICA_TYPE.reduce(
  (total, replicaType) => {
    const replicaKey = key => `${replicaType}.${key}`

    total.push(...[
      { key: replicaType, type: 'label' },
      {
        key: replicaKey('pair'),
        label: 'pair',
        type: 'bool-select',
        path: `spec.flReplicaSpecs.${replicaType}.pair`,
        default: DATASOURCE_TICKET_PARAMS[replicaType].pair,
      },
      {
        key: replicaKey('env'),
        label: 'env',
        type: 'name-value',
        path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].env`,
        emptyDefault: [],
        default: DATASOURCE_TICKET_PARAMS[replicaType].env,
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
        default: DATASOURCE_TICKET_PARAMS[replicaType].command,
        span: 24,
      },
      {
        key: replicaKey('args'),
        label: 'args',
        type: 'json',
        path: `spec.flReplicaSpecs.${replicaType}.template.spec.containers[].args`,
        default: DATASOURCE_TICKET_PARAMS[replicaType].args,
        emptyDefault: [],
        span: 24,
      }
    ])
    return total
  },
  []
)

function fillField(data, field) {
  if (data === undefined) return field
  let v = getValueFromJson(data, field.path || field.key)
  if (typeof v === 'object') {
    v = JSON.stringify(v, null, 2)
  }

  field.value = v
  field.editing = true

  return field
}

function mapValueToFields({data, fields, targetGroup, type = 'form'}) {
  return produce(fields, draft => {
    draft.map((x) => {
      x.value = data[x.key] || x.emptyDefault || ''

      if (x.groupName === targetGroup) {
        x.fields[type].forEach(field => fillField(data[x.groupName], field))
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

export default function TicketList() {
  const { data, mutate } = useSWR('tickets', fetcher);
  const tickets = data ? data.data : null;
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
          draft[groupName] = JSON.parse(data[groupName][groupName])
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
        console.log(formMeta)
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
  const DEFAULT_FIELDS = [
    { key: 'name', required: true },
    { key: 'federation_id', type: 'federation', label: 'federation', required: true },
    {
      key: 'job_type',
      type: 'jobType',
      props: {type: 'datasource'},
      required: true,
      onChange: value => {
        jobType = value
        setFields(handleFields(fields))
      },
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
  const toggleForm = () => setFormVisible(!formVisible);
  const onOk = (ticket) => {
    mutate({
      data: [...tickets, ticket],
    });
    toggleForm();
  };
  const handleEdit = (ticket) => {
    setCurrentTicket(ticket);
    setFields(mapValueToFields({data: ticket, fields}));
    setFormVisible(true);
  };
  const handleSubmit = (value) => {
    const json = {
      ...value,
      public_params: value.public_params ? JSON.parse(value.public_params) : null,
      private_params: value.private_params ? JSON.parse(value.private_params) : null,
    };

    if (currentTicket) {
      return updateTicket(currentTicket.id, json);
    }

    return createTicket(json);
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
            onCancel={toggleForm}
          />
        )
        : (
          <>
            <div className="heading">
              <Text h2>Tickets</Text>
              <Button auto type="secondary" onClick={toggleForm}>Create Ticket</Button>
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