import React, { useMemo, useState, useCallback } from 'react';
import css from 'styled-jsx/css';
import { Link, Text, Input, Fieldset, Button, Card, Description, useTheme, useInput } from '@zeit-ui/react';
import Search from '@zeit-ui/react-icons/search';
import NextLink from 'next/link';
import useSWR from 'swr';
import produce from 'immer'

import { fetcher } from '../../../libs/http';
import { FLAppStatus, handleStatus, getStatusColor } from '../../../utils/job';
import Layout from '../../../components/Layout';
import PopConfirm from '../../../components/PopConfirm';
import Dot from '../../../components/Dot';
import Empty from '../../../components/Empty';
import { deleteJob, createJob } from '../../../services/job';
import Form from '../../../components/Form';
import { DATASOURCE_REPLICA_TYPE, DATASOURCE_PUBLIC_PARAMS } from '../../../constants/form-default'
import { loadAll } from 'js-yaml';

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

export default function JobList(props) {
  const theme = useTheme();
  const styles = useStyles(theme);

  const { data, mutate } = useSWR('jobs', fetcher);
  const jobs = data ? data.data.filter(x => x.metadata) : null

  let federationId = null, jobType = null
  const DEFAULT_FIELDS = useMemo(() => [
    {
      key: 'name',
      required: true,
      path: DATASOURCE_REPLICA_TYPE.reduce((total, currType) => {
        total[currType] = `spec. flReplicaSpecs.${currType}.template.spec.containers.env.DATA_SOURCE_NAME`
        return total
      }, {})
    },
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
    {
      key: 'raw_data',
      type: 'rawData',
    },
    {
      key: 'client_ticket_name',
      type: 'clientTicket',
      label: 'client_ticket',
      props: {
        job_type: null,
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
    },
    {
      key: 'server_ticket_name',
      type: 'serverTicket',
      label: 'server_ticket',
      required: true,
      props: {
        federation_id: null,
        job_type: null,
      },
    },
    ...['client_params', 'server_params'].map(paramsType => ({
      groupName: paramsType,
      initialVisible: false,
      fields: [
        { key: 'env', type: 'name-value', span: 24 },
        ...DATASOURCE_REPLICA_TYPE.reduce((total, currType) => {
          total.push(...[
            { key: currType + ' resources', type: 'label' },
            {
              key: currType + '.cup_request',
              label: 'cpu request',
              span: 12,
              default: '2000m'
            },
            {
              key: currType + '.cup_limit',
              label: 'cpu limit',
              span: 12,
              default: '2000m'
            },
            {
              key: currType + '.cup_limit',
              label: 'memory request',
              span: 12,
              default: '2Gi'
            },
            {
              key: 'memory limit',
              span: 12,
              default: '2Gi'
            },
          ])
          return total
        }, []),
      ]
    }))
  ], [])

  let [fields, setFields] = useState(DEFAULT_FIELDS)

  function mapValueToFields(job, fields) {
    return produce(fields, draft => {
      draft.map((x) => {
        x.value = job.localdata[x.key] || ''

        if ((x.key === 'client_params' || x.key === 'server_params') && x.value) {
          x.value = JSON.stringify(x.value, null, 2);
        }

      });
    })
  }

  const handleFields = fields => produce(fields, draft => {
    draft.map(field => {
      if (field.key === 'client_ticket_name') {
        console.log(jobType)
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
        list: allList.list.filter((item) => item.status.appState === status),
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
    }
    setFormVisible(visible => !visible)
  }, [formVisible]);
  const onOk = () => {
    mutate();
    toggleForm();
  };
  const onCreateJob = (form) => {
    const params = {
      ...form,
      client_params: form.client_params ? JSON.parse(form.client_params) : {},
      server_params: form.server_params ? JSON.parse(form.server_params) : {},
    };
    return createJob(params);
  };

  const handleClone = (item) => {
    setFields(mapValueToFields(item, fields))
    // fields = mapValueToFields(item, DEFAULT_FIELDS)
    toggleForm()
  }

  const renderOperation = item => (
    <>
      <NextLink
        href={`/job/${item.localdata.id}`}
      >
        <Link color>View Detail</Link>
      </NextLink>
      <NextLink
        href={`/job/charts/${item.localdata.id}`}
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
                                                  <Dot color={getStatusColor(item.status.appState)} />
                                                  {handleStatus(item.status.appState)}
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
