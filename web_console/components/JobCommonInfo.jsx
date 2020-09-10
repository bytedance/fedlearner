import React, { useMemo } from 'react';
import css from 'styled-jsx/css';
import { Table, Link, Text, Card, Description, Popover, useTheme, Button } from '@zeit-ui/react';
import useSWR from 'swr';

import { fetcher } from '../libs/http';
import { getStatusColor, handleStatus, FLAppStatus } from '../utils/job';
import Layout from './Layout';
import Dot from './Dot';
import Empty from './Empty';

const podStatus = {
  active: 'active',
  succeeded: 'succeeded',
  failed: 'failed',
};

const parsePods = (PodStatus) => {
  const list = [];
  Object.keys(PodStatus).forEach((type) => {
    Object.values(podStatus).forEach((status) => {
      const pods = PodStatus[type][status];
      Object.keys(pods).forEach((name) => {
        list.push({
          type,
          status,
          name,
        })
      })
    })
  })
  return list;
}

export const jsonHandledPopover = (json, length = 30) => {
  if (!json) return '-';
  const str = JSON.stringify(json, null, 2).replace(/(^")|("$)/g, '');
  let inner = str;
  if (str.length > length) {
    inner = `${str.substring(0, length)}...`;
  }
  return (
    <Popover
      trigger="hover"
      placement="rightEnd"
      content={(
        <div style={{ maxHeight: '400px', maxWidth: '800px', overflow: 'auto' }}>
          <pre style={{ padding: '0 20px', textAlign: 'left' }}>{str}</pre>
        </div>
      )}
    >
      {inner}
    </Popover>
  );
};

function useStyles(theme) {
  return css`
    .page-wrap {
      display: flex;
      flex-wrap: wrap;
      margin: ${theme.layout.pageMargin} 0;
    }
    .right {
      margin-left: ${theme.layout.pageMargin};
      width: 76%;
    }
    .log-wrap {
      min-height: 200px;
      max-height: 400px;
      margin-bottom: ${theme.layout.pageMargin};
      overflow: auto;
    }
    .logs {
      text-align: left;
      white-space: pre-wrap;
    }
  `;
}

export default function JobCommonInfo(props) {
  const theme = useTheme();
  const styles = useStyles(theme);
  const job = props.job;
  const pods = useMemo(() => job?.status?.flReplicaStatus ? parsePods(job.status.flReplicaStatus) : null, [job]);
  const start_time = job?.metadata?.creationTimestamp
    ? new Date(job.metadata.creationTimestamp).getTime()
    : '';
  const options = useMemo(() => ({
    searchParams: { start_time },
  }), [job]);

  const { data: logsData, error: logsError, isValidating: logsIsValidating } = useSWR(
    job && job.localdata && job.metadata
      ? [`job/${job.localdata.name}/logs`, options]
      : null,
    fetcher,
  );
  const logs = job && job.localdata?.submitted !== false
    ? (logsData && logsData.data) ? logsData.data : ['logs error ' + (logsData?.error || logsError?.message)]
    : null;

  const tableData = useMemo(() => {
    if (pods) {
      return pods.map((item) => ({
        status: item.status,
        pod: item.name.replace(
          `${job.localdata?.name}-${job.spec?.role.toLowerCase()}-${item.type.toLowerCase()}-`,
          '',
        ),
        type: item.type,
        link: (
          <>
            {
              job.status?.appState === FLAppStatus.Running && item.status === podStatus.active
                ? (
                  <Link
                    color
                    style={{ marginRight: 10 }}
                    target="_blank"
                    href={`/job/pod-shell?name=${item.name}`}
                  >
                    Shell
                  </Link>
                )
                : null
            }
            <Link
              color
              target="_blank"
              href={`/job/pod-log?name=${item.name}&time=${start_time}`}
            >
              Log
            </Link>
          </>
        ),
      }));
    }
    return [];
  }, [pods]);

  return (
    <div className="page-job">
      <Layout theme={props.theme} toggleTheme={props.toggleTheme}>
        <div className="page-wrap">
          <Card style={{ flex: 1 }}>
            <Text h4>
              {job?.localdata?.name || '-'}
            </Text>
            <div className="left">
              <Description
                title="Status"
                style={{ width: 140 }}
                content={(
                  <>
                    <Dot color={getStatusColor(job?.status?.appState)} />
                    {handleStatus(job?.status?.appState) || '-'}
                  </>
                )}
              />
              <Description
                title="Create Time"
                style={{ width: 220 }}
                content={job?.metadata?.creationTimestamp || '-'}
              />
              <Description
                title="Role"
                style={{ width: 120 }}
                content={job?.spec?.role || '-'}
              />
              {
                props.children
              }
            </div>
          </Card>
          <div className="right">
            <Card>
              <div className="log-wrap">
                <pre className="logs">
                  {
                    logsIsValidating
                      ? null
                      : logs && logs.length
                        ? logs.map((log, i) => <Text p key={`${i}_${log}`}>{log}</Text>)
                        : 'no logs'
                  }
                </pre>
              </div>
              <Table data={tableData}>
                <Table.Column prop="status" label="status" />
                <Table.Column prop="pod" label="pod" />
                <Table.Column prop="type" label="type" />
                <Table.Column prop="link" label="link" />
              </Table>
              {
                tableData.length
                  ? null
                  : <Empty />
              }
            </Card>
          </div>
        </div>
        <style jsx global>{`
          .page-job h4 {
            word-break: break-all;
          }
          .card .content dl {
            margin-bottom: ${theme.layout.pageMargin};
          }
          .page-job .left dl  {
            margin-top: ${theme.layout.pageMargin};
            width: auto !important;
          }
          .page-job .left dl:first-of-type  {
            margin-top: calc(${theme.layout.pageMargin} + 20px);
          }
        `}</style>
        <style jsx>{styles}</style>
      </Layout>
    </div>
  );
}
