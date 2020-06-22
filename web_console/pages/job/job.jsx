import React, { useMemo } from 'react';
import css from 'styled-jsx/css';
import { Table, Link, Text, Code, Card, Description, useTheme } from '@zeit-ui/react';
import useSWR from 'swr';
import { useRouter } from 'next/router';

import { fetcher } from '../../libs/http';
import { getStatusColor, handleStatus } from './utils';
import Layout from '../../components/Layout';
import Dot from '../../components/Dot';
import Empty from '../../components/Empty';

function useStyles(theme) {
  return css`
    .page-wrap {
      display: flex;
      flex-wrap: wrap;
      margin: ${theme.layout.pageMargin} 0;
    }
    .left {
      display: flex;
      flex-direction: row;
    }
    .right {
      width: 100%;
      margin-top: ${theme.layout.pageMargin};
    }
    .log-wrap {
      min-height: 200px;
      max-height: 400px;
      margin-bottom: ${theme.layout.pageMargin};
      overflow: auto;
    }

    @media screen and (min-width: ${theme.layout.pageWidthWithMargin}) {
      .left {
        display: block;
      }
      .right {
        margin-left: ${theme.layout.pageMargin};
        width: 76%;
        margin-top: 0;
      }
    }
  `;
}

function Job(props) {
  const theme = useTheme();
  const styles = useStyles(theme);

  const router = useRouter();
  const { query } = router;
  const { data: jobData } = useSWR(`job/${query.name}`, fetcher);
  const { data: podsData } = useSWR(`job/${query.name}/pods`, fetcher);

  const flapp = jobData ? jobData.data : null;
  const pods = podsData ? podsData.data : null;

  const tableData = useMemo(() => {
    if (pods && pods.items) {
      return pods.items.map((item) => ({
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
  }, [pods && pods.items]);

  return (
    <div className="page-job">
      <Layout theme={props.theme} toggleTheme={props.toggleTheme}>
        <div className="page-wrap">
          <Card style={{ flex: 1 }}>
            <Text h4>
              {flapp?.metadata?.name || '-'}
            </Text>
            <div className="left">
              <Description
                title="Status"
                style={{ width: 140 }}
                content={(
                  <>
                    <Dot color={getStatusColor(flapp?.status?.appState)} />
                    {handleStatus(flapp?.status?.appState) || '-'}
                  </>
                )}
              />
              <Description
                title="Create Time"
                style={{ width: 220 }}
                content={flapp?.metadata?.creationTimestamp || '-'}
              />
              <Description
                title="Role"
                style={{ width: 120 }}
                content={flapp?.spec?.role || '-'}
              />
            </div>
          </Card>
          <div className="right">
            <Card>
              <div className="log-wrap">
                <Code block>
                  logs
                </Code>
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
          .card .content {
            box-sizing: border-box;
          }
          .page-job h4 {
            word-break: break-all;
          }
          @media screen and (min-width: ${theme.layout.pageWidthWithMargin}) {
            .page-job .left dl  {
              margin-top: ${theme.layout.pageMargin};
              width: auto !important;
            }
            .page-job .left dl:first-of-type  {
              margin-top: calc(${theme.layout.pageMargin} + 20px);
            }
          }
        `}</style>
        <style jsx>{styles}</style>
      </Layout>
    </div>
  );
}

Job.getInitialProps = async function(context) {
  return {}
};

export default Job;
