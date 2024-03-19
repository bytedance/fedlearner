import SharedPageLayout from 'components/SharedPageLayout';
import React, { FC, useMemo, useState } from 'react';
import { generatePath, useHistory } from 'react-router';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantList, useUrlState } from 'hooks';
import './index.less';

import {
  Button,
  Input,
  Popconfirm,
  Table,
  Progress,
  Message,
  Tooltip,
} from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { ColumnProps } from '@arco-design/web-react/es/Table';

import i18n from 'i18n';
import { useTranslation } from 'react-i18next';

import GridRow from 'components/_base/GridRow';
import MoreActions, { ActionItem } from 'components/MoreActions';
import Modal from 'components/Modal';
import TodoPopover from 'components/TodoPopover';
import NoResult from 'components/NoResult';
import WhichParticipant from 'components/WhichParticipant';
import routeMaps from '../routes';

import {
  deleteTrustedJobGroup,
  fetchTrustedJobGroupList,
  launchTrustedJobGroup,
  updateTrustedJobGroup,
} from 'services/trustedCenter';
import { FilterOp } from 'typings/filter';
import {
  AuthStatus,
  TrustedJobGroupItem,
  TrustedJobGroupStatus,
  TicketAuthStatus,
} from 'typings/trustedCenter';
import { formatTimestamp } from 'shared/date';
import { getTicketAuthStatus, getLatestJobStatus } from 'shared/trustedCenter';
import { to } from 'shared/helpers';
import { constructExpressionTree, expression2Filter } from 'shared/filter';
import StateIndicator from 'components/StateIndicator';

export const LIST_QUERY_KEY = 'task_list_query';

type QueryParams = {
  name?: string;
};

const TrustedJobList: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const projectId = useGetCurrentProjectId();
  const participantList = useGetCurrentProjectParticipantList();
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: initFilter(),
  });
  const [commentVisible, setCommentVisible] = useState(false);
  const [comment, setComment] = useState('');
  const [selectedTrustedJobGroup, setSelectedTrustedJobGroup] = useState<TrustedJobGroupItem>();
  const listQueryKey = [LIST_QUERY_KEY, projectId, urlState];
  const initFilterParams = expression2Filter(urlState.filter);
  const [filterParams, setFilterParams] = useState<QueryParams>({
    name: initFilterParams.name || '',
  });

  const listQuery = useQuery(
    [listQueryKey, urlState],
    () => {
      return fetchTrustedJobGroupList(projectId!, urlState);
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const trustedJobListShow = useMemo(() => {
    if (!listQuery.data?.data) {
      return [];
    }
    const trustedJobList = (listQuery.data.data || []).filter(
      (item) => item.is_configured === true,
    );
    return trustedJobList;
  }, [listQuery.data]);

  const isEmpty = trustedJobListShow.length === 0;

  const columns = useMemo<ColumnProps<TrustedJobGroupItem>[]>(
    () => [
      {
        title: '名称',
        dataIndex: 'name',
        name: 'name',
        ellipsis: true,
        render: (name: string, record: TrustedJobGroupItem) => {
          return <Link to={gotoTrustedJobGroupDetail(record)}>{name}</Link>;
        },
      },
      {
        title: '发起方',
        dataIndex: 'creator_name',
        name: 'creator_name',
        render: (_: any, record: TrustedJobGroupItem) => {
          return record.is_creator ? '本方' : <WhichParticipant id={record.creator_id} />;
        },
      },
      {
        title: '授权状态',
        dataIndex: 'ticket_auth_status',
        name: 'ticket_auth_status',
        render: (_: any, record: TrustedJobGroupItem) => {
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
        render: (_: any, record: TrustedJobGroupItem) => {
          return (
            <div className="indicator-with-tip">
              <StateIndicator {...getLatestJobStatus(record)} />
            </div>
          );
        },
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        name: 'created_at',
        sorter(a: TrustedJobGroupItem, b: TrustedJobGroupItem) {
          return a.created_at - b.created_at;
        },
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
      },
      {
        title: '操作',
        dataIndex: 'operation',
        name: 'operation',
        render: (_: any, record: TrustedJobGroupItem) => {
          const actionList = [
            {
              label: '编辑',
              disabled: record.status !== TrustedJobGroupStatus.SUCCEEDED,
              onClick: () => {
                const editPath = generatePath(routeMaps.TrustedJobGroupEdit, {
                  id: record.id,
                  role: record.is_creator ? 'sender' : 'receiver',
                });
                history.push(editPath);
              },
            },
            {
              label: '删除',
              disabled: !record.is_creator,
              onClick: () => {
                Modal.delete({
                  title: `确认删除${record.name || ''}吗?`,
                  content: '删除后，该可信计算将无法进行操作，请谨慎删除',
                  onOk() {
                    deleteTrustedJobGroup(projectId!, record.id)
                      .then(() => {
                        Message.success(t('trusted_center.msg_delete_success'));
                        listQuery.refetch();
                      })
                      .catch((error) => {
                        Message.error(error.message);
                      });
                  },
                });
              },
              danger: true,
            },
          ].filter(Boolean) as ActionItem[];

          return (
            <GridRow left="-20">
              <Button
                type="text"
                onClick={() => {
                  setCommentVisible(true);
                  setSelectedTrustedJobGroup(record);
                }}
                disabled={
                  record.status !== TrustedJobGroupStatus.SUCCEEDED ||
                  record.auth_status !== AuthStatus.AUTHORIZED ||
                  record.unauth_participant_ids?.length !== 0
                }
              >
                {'发起任务'}
              </Button>
              {record.auth_status === AuthStatus.AUTHORIZED ? (
                <Popconfirm
                  title={i18n.t('trusted_center.unauthorized_confirm_title', {
                    name: record.name,
                  })}
                  okText={i18n.t('submit')}
                  cancelText={i18n.t('cancel')}
                  onConfirm={() => onUnauthorizedConfirm(record)}
                >
                  <Button type="text" disabled={record.status !== TrustedJobGroupStatus.SUCCEEDED}>
                    {'撤销'}
                  </Button>
                </Popconfirm>
              ) : (
                <Button
                  type="text"
                  disabled={record.status !== TrustedJobGroupStatus.SUCCEEDED}
                  onClick={() => {
                    updateTrustedJobGroup(projectId!, record.id, {
                      auth_status: AuthStatus.AUTHORIZED,
                    }).then(() => {
                      listQuery.refetch();
                    });
                  }}
                >
                  {'授权'}
                </Button>
              )}
              <MoreActions actionList={actionList} />
            </GridRow>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [listQuery],
  );

  return (
    <SharedPageLayout
      title={i18n.t('menu.label_trusted_center')}
      rightTitle={<TodoPopover.TrustedCenter />}
    >
      <GridRow justify="space-between" align="center">
        <Button
          className={'custom-operation-button'}
          type="primary"
          icon={<IconPlus />}
          onClick={onCreateClick}
        >
          {t('trusted_center.btn_create_trusted_computing')}
        </Button>
        <Input.Search
          allowClear
          defaultValue={filterParams.name}
          onSearch={onSearch}
          onClear={() => onSearch('')}
          placeholder={t('trusted_center.placeholder_search_task')}
        />
      </GridRow>
      <div className="group-list-container">
        {isEmpty ? (
          <NoResult text="暂无工作可信计算任务" />
        ) : (
          <Table
            rowKey="id"
            className="custom-table custom-table-left-side-filter"
            loading={listQuery.isFetching}
            data={trustedJobListShow}
            scroll={{ x: '100%' }}
            columns={columns}
            pagination={{
              showTotal: true,
              hideOnSinglePage: true,
              pageSizeChangeResetCurrent: true,
              total: listQuery.data?.page_meta?.total_items ?? undefined,
              current: Number(urlState.page),
              pageSize: Number(urlState.pageSize),
              onChange: onPageChange,
            }}
          />
        )}
      </div>
      <Modal
        title={t('trusted_center.title_initiate_trusted_job', {
          name: selectedTrustedJobGroup?.name,
        })}
        id={selectedTrustedJobGroup?.id}
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
    </SharedPageLayout>
  );

  function renderUnauthParticipantList(record: any) {
    return (
      <div>
        {participantList.map((item) => {
          return (
            <div>
              {`${item.name} ${
                record.unauth_participant_ids.includes(item.id) ? '未授权' : '已授权'
              }`}
            </div>
          );
        })}
      </div>
    );
  }

  function onUnauthorizedConfirm(record: any) {
    updateTrustedJobGroup(projectId!, record.id, {
      auth_status: AuthStatus.PENDING,
    }).then(() => {
      listQuery.refetch();
    });
  }

  function gotoTrustedJobGroupDetail(record: any) {
    return generatePath(routeMaps.TrustedJobGroupDetail, {
      id: record.id,
      tabType: 'computing',
    });
  }

  function onCreateClick() {
    const createPath = generatePath(routeMaps.TrustedJobGroupCreate, {
      role: 'sender',
    });
    history.push(createPath);
  }

  function onSearch(value: any) {
    constructFilterArray({ name: value });
  }

  function constructFilterArray(value: QueryParams) {
    const expressionNodes = [];
    if (value.name) {
      expressionNodes.push({
        field: 'name',
        op: FilterOp.CONTAIN,
        string_value: value.name,
      });
    }
    const serialization = constructExpressionTree(expressionNodes);
    setFilterParams({
      name: value.name,
    });
    setUrlState((prevState) => ({
      ...prevState,
      filter: serialization,
      page: 1,
    }));
  }

  function onPageChange(page: number, pageSize: number | undefined) {
    setUrlState((prevState) => ({
      ...prevState,
      page,
      pageSize,
    }));
  }

  async function onCommentModalConfirm() {
    const [res, error] = await to(
      launchTrustedJobGroup(projectId!, selectedTrustedJobGroup!.id, {
        comment: comment,
      }),
    );
    setCommentVisible(false);
    if (error) {
      Message.error(error.message);
      return;
    }
    if (res.data) {
      Message.success(t('trusted_center.msg_publish_success'));
      listQuery.refetch();
      return;
    }
  }

  function initFilter() {
    const expressionNodes = [];
    expressionNodes.push({
      field: 'name',
      op: FilterOp.CONTAIN,
      string_value: '',
    });
    return constructExpressionTree(expressionNodes);
  }
};

export default TrustedJobList;
