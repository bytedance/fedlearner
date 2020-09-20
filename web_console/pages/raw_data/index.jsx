import React, { useState, useMemo } from 'react';
import { Table, Button, Card, Text, Link } from '@zeit-ui/react';
import NextLink from 'next/link';
import useSWR from 'swr';
import produce from 'immer'
import Layout from '../../components/Layout';
import Form from '../../components/Form';
// import PopConfirm from '../../components/PopConfirm';
import { fetcher } from '../../libs/http';
import Empty from '../../components/Empty';
import { createRawData } from '../../services/raw_data';
import { fillJSON, getValueFromJson, getParsedValueFromData } from '../../utils/form_utils'
import { RAW_DATA_CONTEXT } from '../../constants/form-default'

const RESOURCE_PATH_PREFIX = 'yaml_spec.spec.flReplicaSpecs.[replicaType].template.spec.containers[].resources'
const IMAGE_PATH = 'yaml_spec.spec.flReplicaSpecs.[replicaType].template.spec.containers[].image'
const WORKER_REPLICAS_PATH = 'yaml_spec.spec.flReplicaSpecs.Worker.replicas'

const DATA_FORMAT_OPTIONS = [
  { label: 'TF_RECORD', value: 'TF_RECORD' },
  { label: 'CSV_DICT', value: 'CSV_DICT' },
]

const CONTEXT_FIELDS = [
  { key: 'file_wildcard', default: '*', default: RAW_DATA_CONTEXT.file_wildcard },
  {
    key: 'input_data_format',
    type: 'select',
    required: true,
    default: RAW_DATA_CONTEXT.input_data_format,
    props: {
      options: DATA_FORMAT_OPTIONS
    }
  },
  {
    key: 'output_data_format',
    type: 'select',
    required: true,
    default: RAW_DATA_CONTEXT.output_data_format,
    props: {
      options: DATA_FORMAT_OPTIONS
    }
  },
  {
    key: 'compressed_type',
    type: 'select',
    required: true,
    default: RAW_DATA_CONTEXT.compressed_type,
    props: {
      options: [
        { label: 'GZIP', value: 'GZIP' },
        { label: 'ZLIB', value: 'ZLIB' },
        { label: 'None', value: 'None' },
      ]
    }
  },
  { key: 'batch_size', default: RAW_DATA_CONTEXT.batch_size },
  { key: 'max_flying_item', default: RAW_DATA_CONTEXT.max_flying_item },
  { key: 'write_buffer_size', default: RAW_DATA_CONTEXT.write_buffer_size },
  { key: 'Master Resources', type: 'label', span: 24},
  {
    key: 'resource.Master.cpu_request',
    label: 'cpu request',
    path: RESOURCE_PATH_PREFIX + '.requests.cpu',
    default: RAW_DATA_CONTEXT.resource_master_cpu_request,
    span: 12,
  },
  {
    key: 'resource.Master.cpu_limit',
    label: 'cpu limit',
    path: RESOURCE_PATH_PREFIX + '.limits.cpu',
    default: RAW_DATA_CONTEXT.resource_master_cpu_limit,
    span: 12
  },
  {
    key: 'resource.Master.memory_request',
    label: 'memory request',
    path: RESOURCE_PATH_PREFIX + '.requests.memory',
    default: RAW_DATA_CONTEXT.resource_master_memory_request,
    span: 12,
  },
  {
    key: 'resource.Master.memory_limit',
    label: 'memory limit',
    path: RESOURCE_PATH_PREFIX + '.limits.memory',
    default: RAW_DATA_CONTEXT.resource_master_memory_limit,
    span: 12
  },
  { key: 'worker Resources', type: 'label', span: 24 },
  {
    key: 'resource.Worker.cpu_request',
    label: 'cpu request',
    path: RESOURCE_PATH_PREFIX + '.limits.cpu',
    default: RAW_DATA_CONTEXT.resource_master_cpu_request,
    span: 12
  },
  {
    key: 'resource.Worker.cpu_limit',
    label: 'cpu limit',
    path: RESOURCE_PATH_PREFIX + '.limits.cpu',
    default: RAW_DATA_CONTEXT.resource_master_cpu_limit,
    span: 12
  },
  {
    key: 'resource.Worker.memory_request',
    label: 'memory request',
    path: RESOURCE_PATH_PREFIX + '.requests.memory',
    default: RAW_DATA_CONTEXT.resource_master_memory_request,
    span: 12,
  },
  {
    key: 'resource.Worker.memory_limit',
    label: 'memory limit',
    path: RESOURCE_PATH_PREFIX + '.limits.memory',
    default: RAW_DATA_CONTEXT.resource_master_memory_limit,
    span: 12
  },
  {
    key: 'num_workers',
    label: 'num workers',
    span: 12,
    default: 4,
    path: WORKER_REPLICAS_PATH
  },
]

function handleContextData(container, data, field) {
  if (field.type === 'label') { return }

  let path = field.path || field.key
  let value = data

  if (field.key.startsWith('resource')) {
    const [, replicaType,] = field.key.split('.')
    path = field.path.replace('[replicaType]', replicaType)
  }

  if (field.key === 'compressed_type') {
    value = data === 'None' ? '' : data
  }

  fillJSON(container, path, value)
}

/**
 * set init value and props of fields
 */
function fillField(data, field) {
  let v = getValueFromJson(data, field.path || field.key)
  if (typeof v === 'object') {
    v = JSON.stringify(v, null, 2)
  }
  if (field.key.startsWith('resource')) {
    const [, replicaType,] = field.key.split('.')
    v = getValueFromJson(data, field.path.replace('[replicaType]', replicaType))
  }
  if (field.key === 'compressed_type') {
    v = v === '' ? 'None' : data
  }

  field.value = v
  field.editing = true

  return field
}

function mapValueToFields({data, fields, type='form'}) {
  return produce(fields, draft => {
    draft.map((x) => {
      if (x.groupName === 'context') {
        x.fields[type].map(item => fillField(data['context'], item))
      } else {
        fillField(data, x)
      }
    })
  })
}

let formMeta = {}
const setFormMeta = value => { formMeta = value }

export default function RawDataList() {
  const { data, mutate } = useSWR('raw_datas', fetcher);
  const rawDatas = data ? data.data : null;
  const columns = [
    'id', 'name', 'federation_id', 'data_portal_type', 'input', 'operation',
  ];

  // form meta convert functions
  const rewriteFields = (draft, data) => {
    // image
    ['Master', 'Worker'].forEach(replicaType => {
      fillJSON(draft.context, IMAGE_PATH.replace('[replicaType]', replicaType), data['image'])
    })
    // output_partition_num
    data['output_partition_num'] &&
      fillJSON(draft.context, WORKER_REPLICAS_PATH, data['output_partition_num'])
  }
  const mapFormMeta2Json = () => {
    let data = {}
    fields.map((x) => {
      if (x.groupName === 'context') {
        data.context = { context_data: formMeta.context }
      } else {
        data[x.key] = formMeta[x.key]
      }
    })
    return data
  }
  const mapFormMeta2Form = () => {
    let data = {}
    fields.map((x) => {
      if (x.groupName === 'context') {
        data.context = formMeta.context
      } else {
        data[x.key] = formMeta[x.key]
      }
    })
    return data
  }
  const writeJson2FormMeta = (data) => {
    setFormMeta(produce(formMeta, draft => {
      fields.map((x) => {
        if (x.groupName === 'context') {
          draft.context = JSON.parse(data.context.context_data)
          rewriteFields(draft, data)
        } else {
          draft[x.key] = getParsedValueFromData(data, x) || draft[x.key]
        }
      })
    }))
  }
  const writeForm2FormMeta = (data) => {
    setFormMeta(produce(formMeta, draft => {
      fields.map(x => {
        if (x.groupName === 'context') {
          if (!draft.context) { draft.context = {} }

          for (let field of CONTEXT_FIELDS) {
            handleContextData(draft.context, data.context[field.key], field)
          }

          rewriteFields(draft, data)
        } else {
          draft[x.key] = getParsedValueFromData(data, x) || draft[x.key]
        }
      })
    }))
  }
  // ---end---
  const switchFormType = (data, currType, targetType) => {
    let newFields
    try {
      if (targetType === 'json') {
        writeForm2FormMeta(data)
        newFields = mapValueToFields({data: mapFormMeta2Json(), fields, type: 'json'})
        setFields(newFields)
      }
      if (targetType === 'form') {
        writeJson2FormMeta(data)
        newFields = mapValueToFields({data: mapFormMeta2Form(), fields, type: 'form'})
        setFields(newFields)
      }
    } catch (error) {
      return { error }
    }
    return { newFields }
  }

  const DEFAULT_FIELDS = useMemo(() => [
    { key: 'name', required: true },
    { key: 'federation_id', type: 'federation', label: 'federation', required: true },
    { key: 'output_partition_num', required: true, default: 4 },
    { key: 'data_portal_type', type: 'dataPortalType', required: true },
    { key: 'input', required: true, label: 'input_base_dir', props: { width: '95%' } },
    { key: 'image', required: true, props: { width: '100%' } },
    // { key: 'output', required: true, label: 'output_base_dir', props: { width: '95%' } },
    // { key: 'context', required: true, type: 'json', span: 24 },
    { key: 'remark', type: 'text', span: 24 },
    {
      groupName: 'context',
      formTypes: ['form', 'json'],
      onFormTypeChange: switchFormType,
      fields: {
        form: CONTEXT_FIELDS,
        json: [
          {
            key: 'context_data',
            type: 'json',
            hideLabel: true,
            span: 24,
            props: {
              minHeight: '500px'
            }
          }
        ]
      }
    },
  ], []);
  const [fields, setFields] = useState(DEFAULT_FIELDS)

  // eslint-disable-next-line arrow-body-style
  const operation = (actions, rowData) => {
    // const onConfirm = () => revokeRawData(rowData.rowValue.id);
    // const onOk = (rawData) => {
    //   mutate({ data: rawDatas.map((x) => (x.id === rawData.id ? rawData : x)) });
    // };
    return (
      <>
        <NextLink
          href={`/raw_data/${rowData.rowValue.id}`}
        >
          <Link color>View Detail</Link>
        </NextLink>
        {/* <PopConfirm onConfirm={() => { }} onOk={() => { }}>
          <Text className="actionText" type="error">Revoke</Text>
        </PopConfirm> */}
      </>
    );
  };
  const dataSource = rawDatas
    ? rawDatas
      .map((x) => {
        const context = JSON.stringify(x.context);
        return {
          ...x,
          context,
          operation,
        };
      })
    : [];
  const [formVisible, setFormVisible] = useState(false);

  const toggleForm = () => setFormVisible(!formVisible);
  const onOk = (rawData) => {
    mutate({
      data: [rawData, ...rawDatas],
    });
    toggleForm();
  };

  const onSubmit = (value, formType) => {
    let writer = formType === 'json' ? writeJson2FormMeta : writeForm2FormMeta
    writer(value)

    return createRawData(formMeta)
  }

  return (
    <Layout>
      {formVisible
        ? (
          <Form
            title="Create Raw Data"
            fields={fields}
            onSubmit={onSubmit}
            onOk={onOk}
            onCancel={toggleForm}
          />
        )
        : (
          <>
            <div className="heading">
              <Text h2>RawDatas</Text>
              <Button auto type="secondary" onClick={toggleForm}>Create Raw Data</Button>
            </div>
            {rawDatas && (
              <Card>
                <Table data={dataSource}>
                  {columns.map((x) => <Table.Column key={x} prop={x} label={x} />)}
                </Table>
                {
                  rawDatas.length
                    ? null
                    : <Empty style={{ paddingBottom: 0 }} />
                }
              </Card>
            )}
          </>
        )}
      <style jsx global>{`
        table {
          word-break: break-word;
        }
        td {
          min-width: 20px;
        }
      `}</style>
    </Layout>
  );
}