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
import {
  DATASOURCE_REPLICA_TYPE,
  DATASOURCE_PUBLIC_PARAMS
} from '../../../constants/form-default'

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

const TICKET_FIELDS = [
  { key: 'name', required: true },
  { key: 'federation_id', type: 'federation', label: 'federation' },
  { key: 'job_type', type: 'jobType', props: {type: 'datasource'}, required: true },
  { key: 'role', type: 'jobRole' },
  { key: 'sdk_version' },
  { key: 'expire_time' },
  {
    key: 'raw_data',
    type: 'rawData',
    higherUpdateForm: updateFormHook =>
      value => updateFormHook('num partitions', value)
  },
  { key: 'num partitions' },
  { key: 'image', span: 24, props: {width: '100%'} },
  { key: 'remark', type: 'text', span: 24 },
  {
    groupName: 'advanced_settings',
    initialVisible: false,
    fields: [
      { key: 'public_params', type: 'json', span: 24},
      ...DATASOURCE_REPLICA_TYPE.reduce((total, currType) => {
        const DEFAULT = DATASOURCE_PUBLIC_PARAMS[currType]
        total.push(...[
          { key: currType, type: 'label' },
          {
            key: currType + '.pair',
            label: 'pair',
            default: DEFAULT['pair'],
            path: `spec.flReplicaSpecs.${currType}.pair`
          },
          {
            key: currType + '.env',
            label: 'env',
            type: 'name-value',
            default: DEFAULT['env'],
            path: `spec.flReplicaSpecs.${currType}.template.spec.containers.env`,
            span: 24
          },
          {
            key: currType + '.command',
            label: 'command',
            type: 'json',
            default: DEFAULT['command'],
            path: `spec.flReplicaSpecs.${currType}.template.spec.containers.command`,
            span: 24
          },
          {
            key: currType + '.args',
            label: 'args',
            type: 'json',
            default: DEFAULT['args'],
            path: `spec.flReplicaSpecs.${currType}.template.spec.containers.args`,
            span: 24
          },
        ])
        return total
      }, []),
    ]
  }
]

const JOB_FIELDS = [
  { key: 'name', required: true },
  {
    key: 'job_type',
    type: 'jobType',
    props: {type: 'datasource', disabled: true},
    required: true
  },
  {
    key: 'raw_data',
    type: 'rawData',
  },
  {
    groupName: 'client_params',
    initialVisible: false,
    fields: [
      { key: 'resources', type: 'label' },
      ...DATASOURCE_REPLICA_TYPE.reduce((total, currType) => {
        total.push(...[
          { key: currType, type: 'label' },
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
      { key: 'env', type: 'name-value', span: 24 }
    ]
  }
]

function setFieldValue (fields, key, value) {
  return produce(fields, draft => {
    draft.forEach(field => {
      if (field.key === key) {
        field.value = value
      }
    })
  })
}

function JobList(props) {

  const theme = useTheme();
  const styles = useStyles(theme);

  const { data, mutate } = useSWR('jobs', fetcher);
  const jobs = data ? data.data?.filter(x => x.metadata) : null;
  const [fields, setFields] = useState(TICKET_FIELDS)

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

  const [ticketFormVisible, setTicketFormVisible] = useState(false)
  const [jobFormVisible, setJobFormVisible] = useState(false)
  const onCreateDataSource = useCallback(() => {
    setTicketFormVisible(true)
  }, [])
  const onCancel = useCallback(() => {
    setTicketFormVisible(false)
    setJobFormVisible(false)
    setFields(TICKET_FIELDS)
  }, [])
  const onOk = () => {
    if (ticketFormVisible) {
      setTicketFormVisible(false)
      setJobFormVisible(true)
    } else if (jobFormVisible) {
      setJobFormVisible(false)
    }
  };
  const onCreateTicket = form => {
    setFields(setFieldValue(JOB_FIELDS, 'job_type', form['job_type']))
    return {}
  }
  const onCreateJob = (form) => {
    setFields(TICKET_FIELDS)
    return {}
  };

  const formTitle = ticketFormVisible ? 'Create Ticket' : 'Create Job'
  const onSubmit = ticketFormVisible ? onCreateTicket : onCreateJob
  return (
    <div className="page-tasks">
      <Layout theme={props.theme} toggleTheme={props.toggleTheme}>
        {ticketFormVisible || jobFormVisible
          ? (
            <Form
              title={formTitle}
              fields={fields}
              onSubmit={onSubmit}
              onOk={onOk}
              onCancel={onCancel}
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
                      <Button auto size="small" type="secondary" onClick={onCreateDataSource}>Create DataSource</Button>
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
                                                content={(
                                                  <>
                                                    <NextLink
                                                      href={`/job/${item.localdata.id}`}
                                                    >
                                                      <Link color>View Detail</Link>
                                                    </NextLink>
                                                    <PopConfirm
                                                      onConfirm={() => deleteJob(item.localdata.id)}
                                                      onOk={() => mutate({ data: jobs.filter((i) => i !== item) })}
                                                    >
                                                      <Text className="actionText" type="error">Delete</Text>
                                                    </PopConfirm>
                                                  </>
                                                )}
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

export default JobList;
