import React, { useMemo, useState, useCallback } from 'react';
import css from 'styled-jsx/css';
import { Link, Text, Input, Fieldset, Button, Card, Description, useTheme, useInput } from '@zeit-ui/react';
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
  DATASOURCE_JOB_REPLICA_TYPE,
} from '../constants/form-default'
import { getParsedValueFromData, fillJSON, getValueFromJson, getValueFromEnv } from '../utils/form_utils';
import { getJobStatus } from '../utils/job'
import { JOB_TYPE } from '../constants/job'

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

  fillJSON(container, path, value)
}

function fillField(data, field) {
  if (data === undefined) return field
  let v = getValueFromJson(data, field.path || field.key) || field.emptyDefault || ''
  if (typeof v === 'object') {
    v = JSON.stringify(v, null, 2)
  }

  field.value = v
  field.editing = true

  return field
}

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
  trainning,
  filter,
  ...props
}) {
  const theme = useTheme();
  const styles = useStyles(theme);

  let JOB_REPLICA_TYPE, NAME_KEY, FILTER_TYPES, PAGE_NAME
  if (datasoure) {

    PAGE_NAME = 'datasource'

    JOB_REPLICA_TYPE = DATASOURCE_JOB_REPLICA_TYPE

    NAME_KEY = 'DATA_SOURCE_NAME'

    FILTER_TYPES = JOB_TYPE.datasource

  } else {

    PAGE_NAME = 'trainning'

    JOB_REPLICA_TYPE = DATASOURCE_JOB_REPLICA_TYPE

    NAME_KEY = 'TRAINNING_NAME'

    FILTER_TYPES = JOB_TYPE.trainning

  }

  filter = filter
      || useCallback(job => FILTER_TYPES.some(type => type === job.localdata.job_type), [])

  const PARAMS_FORM_FIELDS = useMemo(() => JOB_REPLICA_TYPE.reduce((total, currType) => {
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
          ignoreKeys: ['DATA_SOURCE_NAME']
        }
      },
      {
        key: 'resoure.' + currType + '.cup_request',
        label: 'cpu request',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.requests.cpu',
        span: 12,
        default: '2000m'
      },
      {
        key: 'resoure.' + currType + '.cup_limit',
        label: 'cpu limit',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.limits.cpu',
        span: 12,
        default: '2000m'
      },
      {
        key: 'resoure.' + currType + '.memory_request',
        label: 'memory request',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.requests.memory',
        span: 12,
        default: '2Gi'
      },
      {
        key: 'resoure.' + currType + '.memory_limit',
        label: 'memory limit',
        path: RESOURCE_PATH_PREFIX.replace('[replicaType]', currType) + '.limits.memory',
        span: 12,
        default: '2Gi'
      },
    ])
    return total
  }, []), [])

  const { data, mutate } = useSWR('jobs', fetcher);
  const jobs = data ? data.data.filter(el => el.metadata).filter(filter) : null
  // const jobs = mockJobList.data

  let federationId = null, jobType = null

  // form meta convert functions
  const rewriteFields = useCallback((draft, data) => {
    // this function will be call inner immer
    // name
    PARAMS_GROUP.forEach(paramType => {
      JOB_REPLICA_TYPE.forEach(replicaType => {
        if (!draft[paramType]) {
          draft[paramType] = {}
        }
        let envs = getValueFromJson(draft[paramType], ENV_PATH.replace('[replicaType]', replicaType))
        if (!envs) return

        let envNames = envs.map(env => env.name)
        let idx = envNames.indexOf(NAME_KEY)
        if (idx >= 0) {
          envs[idx].value = data.name
        } else {
          // here envs is not extensible, push will throw error
          envs = envs.concat({name: NAME_KEY, value: data.name || ''})
        }
        // trigger immer‘s intercepter
        fillJSON(draft[paramType], ENV_PATH.replace('[replicaType]', replicaType), envs)
      })
    })
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
      fields.map(x => {
        if (x.groupName) {
          if (x.groupName !== groupName) return
          if (!draft[groupName]) { draft[groupName] = {} }

          for (let field of PARAMS_FORM_FIELDS) {
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
  // ---end---
  const DEFAULT_FIELDS = useMemo(() => [
    {
      key: 'name',
      required: true,
    },
    {
      key: 'job_type',
      type: 'jobType',
      props: {type: PAGE_NAME},
      required: true,
      onChange: value => {
        jobType = value
        setFields(handleFields(fields))
      },
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
      key: 'federation_id',
      type: 'federation',
      label: 'federation',
      required: true,
      onChange: value => {
        federationId = value
        setFields(handleFields(fields))
      },
      props: {
        initTrigerChange: true
      }
    },
    {
      key: 'server_ticket_name',
      type: 'serverTicket',
      label: 'server_ticket',
      // required: true,
      props: {
        federation_id: null,
        type: PAGE_NAME,
      },
    },
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
      },
      fields: {
        form: PARAMS_FORM_FIELDS,
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
  ], [])

  let [fields, setFields] = useState(DEFAULT_FIELDS)

  const handleFields = fields => produce(fields, draft => {
    draft.map(field => {
      if (field.key === 'client_ticket_name') {
        field.props.job_type = jobType
      }
      if (field.key === 'server_ticket_name') {
        field.props.federation_id = federationId
      }
    })
  })

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
  const toggleForm = useCallback(() => {
    if (formVisible) {
      setFields(DEFAULT_FIELDS)
      setFormMeta({})
    }
    setFormVisible(visible => !visible)
  }, [formVisible]);
  const onOk = () => {
    mutate();
    toggleForm();
  };
  const onCreateJob = (data, groupFormType) => {
    PARAMS_GROUP.forEach(paramType => {
      switch (groupFormType[paramType]) {
        case 'json':
          writeJson2FormMeta(paramType, data)
          break
        case 'form':
          writeForm2FormMeta(paramType, data)
      }
    })
    return createJob(formMeta);
  };

  const handleClone = (item) => {
    setFormMeta(item.localdata)

    setFields(fields => mapValueToFields({
      data: mapFormMeta2Form(),
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
                    <Button auto size="small" type="secondary" onClick={toggleForm}>Create Job</Button>
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
