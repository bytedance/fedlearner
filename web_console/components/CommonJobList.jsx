import React, { useMemo, useState, useCallback } from 'react';
import css from 'styled-jsx/css';
import { Link, Text, Input, Fieldset, Button, Card, Description, useTheme, useInput, Tooltip } from '@zeit-ui/react';
import AlertCircle from '@geist-ui/react-icons/alertCircle'
import Search from '@zeit-ui/react-icons/search';
import NextLink from 'next/link';
import useSWR from 'swr';
import produce from 'immer'

import { fetcher } from '../libs/http';
import { FLAppStatus, handleStatus, getStatusColor, JobStatus } from '../utils/job';
import Layout from '../components/Layout';
import PopConfirm from '../components/PopConfirm';
import Dot from '../components/Dot';
import Empty from '../components/Empty';
import { deleteJob, createJob } from '../services/job';
import Form from '../components/Form';
import {
  JOB_DATA_JOIN_PARAMS,
  JOB_NN_PARAMS,
  JOB_PSI_DATA_JOIN_PARAMS,
  JOB_TREE_PARAMS,
  JOB_DATA_JOIN_REPLICA_TYPE,
  JOB_NN_REPLICA_TYPE,
  JOB_PSI_DATA_JOIN_REPLICA_TYPE,
  JOB_TREE_REPLICA_TYPE,
} from '../constants/form-default'
import { getParsedValueFromData, fillJSON, getValueFromJson, getValueFromEnv, filterArrayValue } from '../utils/form_utils';
import { getJobStatus } from '../utils/job'
import { JOB_TYPE_CLASS, JOB_TYPE } from '../constants/job'

// import {mockJobList} from '../constants/mock_data'

function useStyles(theme) {
  return css`
    .counts-wrap {
      padding: 0 5%;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .num {
      text-align: center;
      color: ${theme.palette.accents_5};
      margin-bottom: 1em;
    }
    .h {
      font-weight: normal;
      margin: 1em 0;
    }
    .b {
      color: ${theme.palette.accents_6};
      font-size: 1.4em;
    }

    .list-wrap {
      position: relative;
    }
    .filter-bar {
      position: absolute;
      right: 0;
      top: 0;
      display: flex;
      align-items: center;
      justify-content: flex-end;
    }
    .filter-form {
      display: flex;
      align-items: center;
      margin-right: 10px;
    }
    .filter-input {
      width: 200px;
      margin-right: 10px;
    }

    .content-list-wrap {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .content-list {
      padding: 20px 10px;
      border-bottom: 1px solid ${theme.palette.border};
    }
    .content-list:last-of-type {
      border-bottom: none;
    }
    .desc-wrap {
      display: flex;
    }
  `;
}

const RESOURCE_PATH_PREFIX = 'spec.flReplicaSpecs.[replicaType].template.spec.containers[].resources'
const ENV_PATH = 'spec.flReplicaSpecs.[replicaType].template.spec.containers[].env'
const PARAMS_GROUP = ['client_params', 'server_params']

function handleParamData(container, data, field) {
  if (field.type === 'label') { return }

  let path = field.path || field.key
  let value = data

  if (/[/s/S]* num$/.test(field.key)) {
    value = parseInt(value)
  }

  fillJSON(container, path, value)
}

function fillField(data, field) {
  if (data === undefined) return field

  let isSetValueWithEmpty = false
  let disabled = false

  let v = getValueFromJson(data, field.path || field.key) || field.emptyDefault || ''

  if (field.key === 'federation_id') {
    const federationID = parseInt(localStorage.getItem('federationID'))
    if (federationID > 0) {
      v = federationID
      disabled = true
    }
  }
  else if (/[/s/S]* num$/.test(field.key)) {
    let replicaType = field.key.split(' ')[0]
    let path = `spec.flReplicaSpecs.${replicaType}.replicas`
    v = getValueFromJson(data['client_params'], path)
      || getValueFromJson(data['server_params'], path)
  }

  if (typeof v === 'object'  && v !== null) {
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

let federationId = null, jobType = null

const passFieldInfo = fields => produce(fields, draft => {
  draft.map(field => {
    if (field.key === 'client_ticket_name') {
      field.props.job_type = jobType
    }
    if (field.key === 'server_ticket_name') {
      field.props.federation_id = federationId
    }
  })
})

function mapValueToFields({data, fields, targetGroup, type = 'form', init = false}) {
  return produce(fields, draft => {
    draft.map((x) => {

      if (x.groupName) {
        if (!data[x.groupName]) return
        if (!init && x.groupName !== targetGroup) return

        if (x.formTypes) {
          let types = init ? x.formTypes : [type]
          types.forEach(el => {
            x.fields[el].forEach(field => fillField(data[x.groupName], field))
          })
        } else {
          x.fields.forEach(field => fillField(data[x.groupName], field))
        }

      } else {
        fillField(data, x)
      }

    });
  })
}

let formMeta = {}
const setFormMeta = value => { formMeta = value }

export default function JobList({
  datasoure,
  training,
  filter,
  ...props
}) {
  const theme = useTheme();
  const styles = useStyles(theme);

  let JOB_REPLICA_TYPE, NAME_KEY, FILTER_TYPES, PAGE_NAME, INIT_PARAMS, DEFAULT_JOB_TYPE
  if (datasoure) {

    PAGE_NAME = 'datasource'

    JOB_REPLICA_TYPE = JOB_DATA_JOIN_REPLICA_TYPE

    NAME_KEY = 'DATA_SOURCE_NAME'

    FILTER_TYPES = JOB_TYPE_CLASS.datasource

    INIT_PARAMS = JOB_DATA_JOIN_PARAMS

    DEFAULT_JOB_TYPE = JOB_TYPE.data_join

  } else {

    PAGE_NAME = 'training'

    JOB_REPLICA_TYPE = JOB_NN_REPLICA_TYPE

    NAME_KEY = 'TRAINING_NAME'

    FILTER_TYPES = JOB_TYPE_CLASS.training

    INIT_PARAMS = JOB_NN_PARAMS

    DEFAULT_JOB_TYPE = JOB_TYPE.nn_model

  }

  filter = filter
      || useCallback(job => FILTER_TYPES.some(type => type === job.localdata.job_type), [])

  const getParamsFormFields = useCallback(() => JOB_REPLICA_TYPE.reduce((total, currType) => {
    total.push(...[
      { key: currType, type: 'label' },
      {
        key: currType + '.env',
        label: 'env',
        type: 'name-value',
        path: `spec.flReplicaSpecs.${currType}.template.spec.containers[].env`,
        span: 24,
        emptyDefault: [],
        props: {
          ignoreKeys: filterArrayValue([
            datasoure && 'DATA_SOURCE_NAME',
            training && 'TRAINING_NAME',
          ])
        }
      },
      {
        key: 'resoure.' + currType + '.cup_request',
        label: 'cpu request',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.requests.cpu',
        span: 12,
      },
      {
        key: 'resoure.' + currType + '.cup_limit',
        label: 'cpu limit',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.limits.cpu',
        span: 12,
      },
      {
        key: 'resoure.' + currType + '.memory_request',
        label: 'memory request',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.requests.memory',
        span: 12,
      },
      {
        key: 'resoure.' + currType + '.memory_limit',
        label: 'memory limit',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.limits.memory',
        span: 12,
      },
    ])
    return total
  }, []), [RESOURCE_PATH_PREFIX, JOB_REPLICA_TYPE])

  const { data, mutate } = useSWR('jobs', fetcher);
  const jobs = data && data.data ? data.data.filter(el => el.metadata).filter(filter) : null
  // const jobs = mockJobList.data

  // form meta convert functions
  const rewriteFields = useCallback((draft, data) => {
    // this function will be call inner immer
    // env
    const insert2Env = filterArrayValue([
      { name: NAME_KEY, getValue: data => data.name },
    ])

    PARAMS_GROUP.forEach(paramType => {
      JOB_REPLICA_TYPE.forEach(replicaType => {
        if (!draft[paramType]) {
          draft[paramType] = {}
        }
        let envs = getValueFromJson(draft[paramType], ENV_PATH.replace('[replicaType]', replicaType))
        if (!envs) return

        let envNames = envs.map(env => env.name)

        insert2Env.forEach(el => {
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
        fillJSON(draft[paramType], ENV_PATH.replace('[replicaType]', replicaType), envs)

        // replicas
        let path = `spec.flReplicaSpecs.${replicaType}.replicas`
        if (replicaType !== 'Master') {
          let num = parseInt(data[`${replicaType} num`])
          !isNaN(num) && fillJSON(draft[paramType], path, parseInt(data[`${replicaType} num`]))
        }

      })
    })

    // delete useless fields

    JOB_REPLICA_TYPE
      .forEach(replicaType =>
        draft[`${replicaType} num`] && delete draft[`${replicaType} num`]
      )

  }, [JOB_REPLICA_TYPE])
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
        if (x.groupName) {
          if (x.groupName !== groupName) return
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
      let value

      fields.map(x => {
        if (x.groupName) {
          if (x.groupName !== groupName) return
          if (!draft[groupName]) { draft[groupName] = {} }

          for (let field of getParamsFormFields()) {
            value = getParsedValueFromData(data[groupName], field)
            handleParamData(draft[groupName], value, field)
          }

        } else {
          value = getParsedValueFromData(data, x) || draft[x.key]
          handleParamData(draft, value, x)
        }
      })
      rewriteFields(draft, data)
    }))
  }, [])
  // ---end---
  const onJobTypeChange = useCallback((value, totalData, groupFormType) => {
    writeFormMeta(totalData, groupFormType)

    switch (value) {
      case JOB_TYPE.data_join:
        JOB_REPLICA_TYPE = JOB_DATA_JOIN_REPLICA_TYPE
        setFormMeta({...formMeta, ...JOB_DATA_JOIN_PARAMS}); break
      case JOB_TYPE.psi_data_join:
        JOB_REPLICA_TYPE = JOB_PSI_DATA_JOIN_REPLICA_TYPE
        setFormMeta({...formMeta, ...JOB_PSI_DATA_JOIN_PARAMS}); break
      case JOB_TYPE.nn_model:
        JOB_REPLICA_TYPE = JOB_NN_REPLICA_TYPE
        setFormMeta({...formMeta, ...JOB_NN_PARAMS}); break
      case JOB_TYPE.tree_model:
        JOB_REPLICA_TYPE = JOB_TREE_REPLICA_TYPE
        setFormMeta({...formMeta, ...JOB_TREE_PARAMS}); break
    }

    jobType = value

    setFields(
      passFieldInfo(mapValueToFields({
        data: mapFormMeta2FullData(fields),
        fields: getDefaultFields(),
        init: true,
      }))
    )
  }, [])
  const getDefaultFields = useCallback(() => filterArrayValue([
    {
      key: 'name',
      required: true,
    },
    {
      key: 'job_type',
      type: 'jobType',
      props: {type: PAGE_NAME},
      required: true,
      label: (
        <>
          <span style={{paddingRight: '4px'}}>job_type</span>
          <Tooltip style={{color: '#444'}} text={<span className="formItemLabel">change job type will reset all params</span>}>
            <span style={{position: 'relative', top: '4px'}}><AlertCircle size={16}/></span>
          </Tooltip>
        </>
      ),
      default: DEFAULT_JOB_TYPE,
      onChange: onJobTypeChange,
    },
    {
      key: 'federation_id',
      type: 'federation',
      label: 'federation',
      required: true,
      onChange: (value, formData) => {
        federationId = value
        setFields(fields => passFieldInfo(mapValueToFields({data: formData, fields})))
      },
      props: {
        initTrigerChange: true
      }
    },
    {
      key: 'client_ticket_name',
      type: 'clientTicket',
      label: 'client_ticket',
      props: {
        type: PAGE_NAME,
      },
      required: true
    },
    {
      key: 'server_ticket_name',
      type: 'serverTicket',
      label: 'server_ticket',
      required: true,
      props: {
        federation_id: null,
        type: PAGE_NAME,
      },
    },
    ...JOB_REPLICA_TYPE
      .filter(el => training && el !== 'Master')
      .map(replicaType => ({
        key: `${replicaType} num`,
      })),
    ...PARAMS_GROUP.map(paramsType => ({
      groupName: paramsType,
      initialVisible: false,
      formTypes: ['form', 'json'],
      onFormTypeChange: (data, currType, targetType) => {
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
      },
      fields: {
        form: getParamsFormFields(),
        json: [
          {
            key: paramsType,
            type: 'json',
            span: 24,
            hideLabel: true,
            props: {
              minHeight: '500px'
            },
          },
        ]
      }
    }))
  ]), [JOB_REPLICA_TYPE])

  let [fields, setFields] = useState(getDefaultFields())

  const labeledList = useMemo(() => {
    const allList = { name: 'All', list: jobs || [] };
    return Object.entries(FLAppStatus).reduce((prev, [key, status]) => {
      return prev.concat({
        name: key,
        list: allList.list.filter((item) => item.status?.appState === status),
      });
    }, [allList]);
  }, [jobs]);

  const [label, setLabel] = useState('All');
  const switchLabel = useCallback((l) => setLabel(l), []);

  const searchIcon = useMemo(() => <Search />, []);
  const [filterText, setFilterText] = useState('');
  const { state: inputText, reset, bindings } = useInput('');
  const search = useCallback((e) => {
    e.preventDefault();
    setFilterText(inputText);
  }, [inputText]);
  const resetSearch = useCallback(() => {
    reset();
    setFilterText('');
  }, [reset, setFilterText]);

  const showingList = useMemo(() => {
    const target = labeledList.find(({ name }) => name === label);
    return ((target && target.list) || []).filter((item) => {
      return !filterText || item.localdata.name.indexOf(filterText) > -1;
    });
  }, [label, labeledList, filterText]);

  const [formVisible, setFormVisible] = useState(false);

  const onClickCreate = () => {
    setFormMeta({...INIT_PARAMS})
    setFields(mapValueToFields({data: mapFormMeta2FullData(fields), fields, init: true}))
    toggleForm()
  }
  const toggleForm = useCallback(() => {
    if (formVisible) {
      setFields(getDefaultFields())
      setFormMeta({})
    }
    setFormVisible(visible => !visible)
  }, [formVisible]);
  const onOk = () => {
    mutate();
    toggleForm();
  };

  const writeFormMeta = (data, groupFormType) => {
    PARAMS_GROUP.forEach(paramType => {
      switch (groupFormType[paramType]) {
        case 'json':
          writeJson2FormMeta(paramType, data)
          break
        case 'form':
          writeForm2FormMeta(paramType, data)
      }
    })
  }
  const onCreateJob = (data, groupFormType) => {
    writeFormMeta(data, groupFormType)
    return createJob(formMeta);
  };

  const handleClone = (item) => {
    setFormMeta(item.localdata)

    setFields(fields => mapValueToFields({
      data: mapFormMeta2FullData(fields),
      fields,
      type: 'form',
      init: true
    }))

    toggleForm()
  }

  const renderOperation = item => (
    <>
      <NextLink
        href={`/${PAGE_NAME}/job/${item.localdata.id}`}
      >
        <Link color>View Detail</Link>
      </NextLink>
      <NextLink
        href={`/charts/${item.localdata.id}`}
      >
        <Link color>View Charts</Link>
      </NextLink>
      <Text
        className="actionText"
        onClick={() => handleClone(item)}
        type="success"
        style={{marginRight: `${theme.layout.gap}`}}
      >
        Clone
      </Text>
      <PopConfirm
        onConfirm={() => deleteJob(item.localdata.id)}
        onOk={() => mutate({ data: jobs.filter((i) => i !== item) })}
      >
        <Text className="actionText" type="error">Delete</Text>
      </PopConfirm>
    </>
  )

  return (
    <div className="page-tasks">
      <Layout theme={props.theme} toggleTheme={props.toggleTheme}>
        {formVisible
          ? (
            <Form
              title="Create Job"
              fields={fields}
              onSubmit={onCreateJob}
              onOk={onOk}
              onCancel={toggleForm}
            />
          )
          : (
            <>
              <Card style={{ marginTop: theme.layout.pageMargin }}>
                <div className="counts-wrap">
                  {
                    labeledList.map(({ name, list }) => (
                      <div className="num" key={name}>
                        <h4 className="h">{name}</h4>
                        <b className="b">{data ? list.length : '-'}</b>
                      </div>
                    ))
                  }
                </div>
              </Card>
              <Card style={{ margin: `${theme.layout.pageMargin} 0` }}>
                <div className="list-wrap">
                  <div className="filter-bar">
                    <form onSubmit={search} className="filter-form">
                      <Input
                        {...bindings}
                        placeholder="Search by name"
                        size="small"
                        clearable
                        onClearClick={resetSearch}
                        iconRight={searchIcon}
                        iconClickable
                        onIconClick={search}
                      />
                    </form>
                    <Button auto size="small" type="secondary" onClick={onClickCreate}>Create Job</Button>
                  </div>
                  <Fieldset.Group value={label} onChange={switchLabel}>
                    {
                      labeledList.map(({ name }) => (
                        <Fieldset label={name} key={name}>
                          {
                            label === name
                              ? showingList.length
                                ? (
                                  <ul className="content-list-wrap">
                                    {
                                      showingList.map((item) => (
                                        <li key={item.metadata.selfLink} className="content-list">
                                          <Text h3 title={item.localdata.name}>
                                            {item.localdata.name}
                                          </Text>
                                          <div className="desc-wrap">
                                            <Description
                                              title="Status"
                                              style={{ width: 140 }}
                                              content={(
                                                <>
                                                  <Dot color={getStatusColor(getJobStatus(item))} />
                                                  {getJobStatus(item)}
                                                </>
                                              )}
                                            />
                                            <Description
                                              title="Create Time"
                                              style={{ width: 220 }}
                                              content={item.metadata.creationTimestamp}
                                            />
                                            <Description
                                              title="Role"
                                              style={{ width: 120 }}
                                              content={item.spec.role}
                                            />
                                            <Description
                                              title="Operation"
                                              content={renderOperation(item)}
                                            />
                                          </div>
                                        </li>
                                      ))
                                    }
                                  </ul>
                                )
                                : <Empty />
                              : null
                          }
                        </Fieldset>
                      ))
                    }
                  </Fieldset.Group>
                </div>
              </Card>
            </>
          )
        }
        <style jsx global>{`
          .page-tasks .group, .group button {
            height: 42px;
          }
          .page-tasks .content-list-wrap .link {
            margin-right: ${theme.layout.pageMargin};
          }
          .page-tasks h3 {
            word-break: break-all;
          }
          .page-tasks dd {
            display: flex;
            align-items: center;
          }
        `}</style>
        <style jsx>{styles}</style>
      </Layout>
    </div>
  );
}
