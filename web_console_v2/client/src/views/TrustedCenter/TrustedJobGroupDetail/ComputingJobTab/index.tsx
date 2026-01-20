import { Button, Input, Message, Progress, Table, Tooltip } from '@arco-design/web-react';
import NoResult from 'components/NoResult';
import GridRow from 'components/_base/GridRow';
import Modal from 'components/Modal';
import dayjs from 'dayjs';
import { useGetCurrentProjectId, useUrlState } from 'hooks';
import React, { FC, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';
import { useParams } from 'react-router';
import { useToggle } from 'react-use';
import {
  exportTrustedJobResult,
  fetchTrustedJobList,
  stopTrustedJob,
  updateTrustedJob,
} from 'services/trustedCenter';
import CONSTANTS from 'shared/constants';
import { formatTimestamp } from 'shared/date';
import {
  AuthStatus,
  TicketAuthStatus,
  TrustedJobGroup,
  TrustedJobGroupTabType,
  TrustedJobListItem,
  TrustedJobStatus,
} from 'typings/trustedCenter';
import { Edit } from 'components/IconPark';
import CountTime from 'components/CountTime';
import StateIndicator from 'components/StateIndicator';
import { getTicketAuthStatus, getTrustedJobStatus } from 'shared/trustedCenter';
import { to } from 'shared/helpers';
import TrustedJobDetail from 'views/TrustedCenter/TrustedJobDetail';
import { AuthStatusMap } from 'views/TrustedCenter/shared';

export type Props = {
  trustedJobGroup: TrustedJobGroup;
};

const ComputingJobTab: FC<Props> = ({ trustedJobGroup }) => {
  const { t } = useTranslation();
  const projectId = useGetCurrentProjectId();
  const params = useParams<{ id: string; tabType: TrustedJobGroupTabType }>();
  const [commentVisible, setCommentVisible] = useState(false);
  const [comment, setComment] = useState('');
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
      return fetchTrustedJobList(projectId!, { trusted_job_group_id: params.id });
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
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
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
        title: '备注',
        dataIndex: 'comment',
        name: 'comment',
        width: 180,
        render: (_: any, record: TrustedJobListItem) => {
          return (
            <GridRow>
              {record.comment ? (
                <Tooltip position="tl" content={record.comment}>
                  <div className="col-description">{record.comment}</div>
                </Tooltip>
              ) : (
                <></>
              )}

              <Button
                type="text"
                size="mini"
                icon={<Edit />}
                onClick={() => {
                  setTrustedJobId(record.id);
                  setComment(record.comment);
                  setCommentVisible(true);
                }}
              />
            </GridRow>
          );
        },
      },
      {
        title: t('trusted_center.col_trusted_job_operation'),
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
              <Button
                type="text"
                disabled={record.status !== TrustedJobStatus.SUCCEEDED}
                size="mini"
                onClick={() => {
                  Modal.confirm({
                    title: `可信数据导出申请`,
                    content: '导出需要工作区合作伙伴共同审批，是否确认发起申请？',
                    onOk() {
                      exportTrustedJobResult(projectId!, record.id)
                        .then(() => {
                          Message.success('开始导出，请在数据中心-结果数据集查看导出结果');
                        })
                        .catch((error) => {
                          Message.error(error.message);
                        });
                    },
                  });
                }}
              >
                {'导出'}
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
          <NoResult text="暂无可信计算任务" />
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
      <Modal
        title={t('trusted_center.title_edit_trusted_job', { name: trustedJobGroup?.name })}
        id={trustedJobId}
        visible={commentVisible}
        onOk={() => onCommentModalConfirm()}
        onCancel={() => {
          setCommentVisible(false);
          setComment('');
        }}
        autoFocus={false}
        focusLock={true}
      >
        <div className="modal-label">{t('trusted_center.label_trusted_job_comment')}</div>
        <Input.TextArea
          placeholder={t('trusted_center.placeholder_trusted_job_set_comment')}
          autoSize={{ minRows: 3 }}
          value={comment}
          onChange={setComment}
        />
      </Modal>
      <TrustedJobDetail
        visible={drawerVisible}
        group={trustedJobGroup!}
        toggleVisible={toggleDrawerVisible}
        id={trustedJobId}
        jobId={selectedJobId}
      />
    </div>
  );

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

  async function onCommentModalConfirm() {
    const [res, error] = await to(
      updateTrustedJob(projectId!, trustedJobId!, {
        comment: comment,
      }),
    );
    setCommentVisible(false);
    setComment('');
    if (error) {
      Message.error(error.message);
      return;
    }
    if (res.data) {
      const msg = '编辑成功';
      Message.success(msg);
      listQuery.refetch();
      return;
    }
  }

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
};

export default ComputingJobTab;
