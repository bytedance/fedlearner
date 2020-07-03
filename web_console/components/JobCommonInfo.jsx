import React, { useMemo } from 'react';
import css from 'styled-jsx/css';
import { Table, Link, Text, Card, Description, Popover, useTheme } from '@zeit-ui/react';
import useSWR from 'swr';

import { fetcher } from '../libs/http';
import { getStatusColor, handleStatus } from '../utils/job';
import Layout from './Layout';
import Dot from './Dot';
import Empty from './Empty';

export const jsonHandledPopover = (json, length = 30) => {
  if (!json) return '-';
  const str = JSON.stringify(json, null, 2);
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

  const { data: podsData } = useSWR(`job/${job && job.localdata?.k8s_name}/pods`, fetcher);
  const pods = podsData ? podsData.data : null;

  const { data: logsData, error: logsError, isValidating: logsIsValidating } = useSWR(`job/${job && job.localdata?.k8s_name}/logs/${new Date(job && job.metadata?.creationTimestamp).getTime()}`, fetcher);
  const logs = (logsData && logsData.data) ? logsData.data : ['logs error ' + (logsData?.error || logsError?.message)]

  const tableData = useMemo(() => {
    if (pods) {
      return pods.map((item) => ({
        status: item.status.phase,
        pod: item.metadata.name.replace(`${
            item.metadata.labels['app-name']
          }-${
            item.metadata.labels.role
          }-${
            item.metadata.labels['fl-replica-type']
          }-${
            item.metadata.labels['fl-replica-index']
          }-`, ''),
        type: item.metadata.labels['fl-replica-type'],
        startupTime: item.metadata.creationTimestamp,
        link: (
          <>
            {
              item.status.phase === 'Running'
              ? (
                <Link
                  color
                  style={{ marginRight: 10 }}
                  target="_blank"
                  href={`/job/pod-shell?name=${item.metadata.name}&container=${
                    item.status.containerStatuses && item.status.containerStatuses.length
                      ? item.status.containerStatuses[0].name
                      : ''
                  }`}
                >
                  Shell
                </Link>
              )
              : null
            }
            <Link
              color
              target="_blank"
              href={`/job/pod-log?name=${item.metadata.name}&time=${new Date(item.metadata.creationTimestamp).getTime()}`}
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
                        ? logs.map((log) => <Text p>{log}</Text>)
                        : 'no logs'
                  }
                </pre>
              </div>
              <Table data={tableData}>
                <Table.Column prop="status" label="status" />
                <Table.Column prop="pod" label="pod" />
                <Table.Column prop="type" label="type" />
                <Table.Column prop="startupTime" label="start-up time" />
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
