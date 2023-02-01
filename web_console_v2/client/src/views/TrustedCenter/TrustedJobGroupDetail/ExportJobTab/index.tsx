import { Button, Message, Progress, Table, Tooltip } from '@arco-design/web-react';
import NoResult from 'components/NoResult';
import GridRow from 'components/_base/GridRow';
import Modal from 'components/Modal';
import dayjs from 'dayjs';
import { useGetCurrentProjectId, useUrlState } from 'hooks';
import React, { FC, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { useParams } from 'react-router';
import { useToggle } from 'react-use';
import { fetchTrustedJobList, stopTrustedJob } from 'services/trustedCenter';
import CONSTANTS from 'shared/constants';
import { formatTimestamp } from 'shared/date';
import {
  AuthStatus,
  TicketAuthStatus,
  TrustedJobGroupTabType,
  TrustedJobListItem,
  TrustedJobParamType,
  TrustedJobStatus,
} from 'typings/trustedCenter';
import CountTime from 'components/CountTime';
import StateIndicator from 'components/StateIndicator';
import { getTicketAuthStatus, getTrustedJobStatus } from 'shared/trustedCenter';
import ExportJobDetailDrawer from '../ExportJobDetailDrawer';
import { AuthStatusMap } from 'views/TrustedCenter/shared';

const ExportJobTab: FC = () => {
  const projectId = useGetCurrentProjectId();
  const params = useParams<{ id: string; tabType: TrustedJobGroupTabType }>();
  const [trustedJobId, setTrustedJobId] = useState<ID>();
  const [selectedJobId, setSelectedJobId] = useState<ID>();
  const [drawerVisible, toggleDrawerVisible] = useToggle(false);
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: '',
  });

  const listQuery = useQuery(
    ['trustedJobListQuery', params],
    () => {
      return fetchTrustedJobList(projectId!, {
        trusted_job_group_id: params.id,
        type: TrustedJobParamType.EXPORT,
      });
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const columns = useMemo(
    () => [
      {
        title: '名称',
        dataIndex: 'name',
        name: 'name',
        ellipsis: true,
        render: (name: string, record: TrustedJobListItem) => {
          return (
            <GridRow left={-13}>
              <Button type="text" size="mini" onClick={() => onCheck(record)}>
                {name}
              </Button>
            </GridRow>
          );
        },
      },
      {
        title: '授权状态',
        dataIndex: 'ticket_auth_status',
        name: 'ticket_auth_status',
        render: (_: any, record: TrustedJobListItem) => {
          const data = getTicketAuthStatus(record);
          return (
            <>
              <Tooltip
                position="tl"
                content={
                  record.ticket_auth_status === TicketAuthStatus.AUTH_PENDING
                    ? renderUnauthParticipantList(record)
                    : undefined
                }
              >
                <div>{data.text}</div>
              </Tooltip>
              <Progress
                percent={data.percent}
                showText={false}
                style={{ width: 100 }}
                status={data.type}
              />
            </>
          );
        },
      },
      {
        title: '任务状态',
        dataIndex: 'status',
        name: 'status',
        render: (_: any, record: TrustedJobListItem) => {
          return (
            <div className="indicator-with-tip">
              <StateIndicator {...getTrustedJobStatus(record)} />
            </div>
          );
        },
      },
      {
        title: '运行时长',
        dataIndex: 'runtime',
        name: 'runtime',
        render: (_: any, record: TrustedJobListItem) => {
          let isRunning = false;
          let isStopped = true;
          let runningTime = 0;

          const { status } = record;
          const { PENDING, RUNNING, STOPPED, SUCCEEDED, FAILED } = TrustedJobStatus;
          isRunning = [RUNNING, PENDING].includes(status);
          isStopped = [STOPPED, SUCCEEDED, FAILED].includes(status);

          if (isRunning || isStopped) {
            const { finished_at, started_at } = record;
            runningTime = isStopped ? finished_at! - started_at! : dayjs().unix() - started_at!;
          }
          return <CountTime time={runningTime} isStatic={!isRunning} />;
        },
      },
      {
        title: '开始时间',
        dataIndex: 'started_at',
        name: 'started_at',
        sorter(a: TrustedJobListItem, b: TrustedJobListItem) {
          return a.started_at - b.started_at;
        },
        render: (date: number) => (
          <div>{date ? formatTimestamp(date) : CONSTANTS.EMPTY_PLACEHOLDER}</div>
        ),
      },
      {
        title: '结束时间',
        dataIndex: 'finished_at',
        name: 'finished_at',
        sorter(a: TrustedJobListItem, b: TrustedJobListItem) {
          return a.finished_at - b.finished_at;
        },
        render: (date: number) => (
          <div>{date ? formatTimestamp(date) : CONSTANTS.EMPTY_PLACEHOLDER}</div>
        ),
      },
      {
        title: '操作',
        dataIndex: 'operation',
        name: 'operation',
        render: (_: any, record: TrustedJobListItem) => {
          return (
            <GridRow left={-15}>
              <Button
                disabled={record.status !== TrustedJobStatus.RUNNING}
                type="text"
                size="mini"
                onClick={() => {
                  Modal.terminate({
                    title: `确认终止${record.name || ''}吗?`,
                    content: '终止后，该任务将无法重启，请谨慎操作',
                    onOk() {
                      stopTrustedJob(projectId!, record.id)
                        .then(() => {
                          Message.success('终止成功！');
                          listQuery.refetch();
                        })
                        .catch((error) => {
                          Message.error(error.message);
                        });
                    },
                  });
                }}
              >
                {'终止'}
              </Button>
            </GridRow>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const listShow = useMemo(() => {
    if (!listQuery.data?.data) {
      return [];
    }
    const trustedJobList = listQuery.data.data || [];
    return trustedJobList;
  }, [listQuery.data]);

  const isEmpty = false;

  return (
    <div>
      <div className="list-container">
        {isEmpty ? (
          <NoResult text="暂无导出任务" />
        ) : (
          <Table
            rowKey="id"
            className="custom-table custom-table-left-side-filter"
            loading={listQuery.isFetching}
            data={listShow}
            scroll={{ x: '100%' }}
            columns={columns}
            pagination={{
              showTotal: true,
              pageSizeChangeResetCurrent: true,
              hideOnSinglePage: true,
              total: listQuery.data?.page_meta?.total_items ?? undefined,
              current: Number(urlState.page),
              pageSize: Number(urlState.pageSize),
              onChange: onPageChange,
            }}
          />
        )}
      </div>
      <ExportJobDetailDrawer
        visible={drawerVisible}
        toggleVisible={toggleDrawerVisible}
        id={trustedJobId}
        jobId={selectedJobId}
      />
    </div>
  );

  function renderUnauthParticipantList(record: any) {
    return (
      <div>
        {Object.keys(record.participants_info.participants_map).map((key) => {
          return (
            <div>{`${key} ${
              AuthStatusMap[
                record.participants_info?.participants_map[key].auth_status as AuthStatus
              ]
            }`}</div>
          );
        })}
      </div>
    );
  }

  function onPageChange(page: number, pageSize: number | undefined) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }

  function onCheck(record: any) {
    setTrustedJobId(record.id);
    setSelectedJobId(record.job_id);
    toggleDrawerVisible(true);
  }
};

export default ExportJobTab;
