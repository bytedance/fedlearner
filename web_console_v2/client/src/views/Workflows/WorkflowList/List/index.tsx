import React, { FC, useMemo, useState } from 'react';
import { Form, Grid, Button, Input, Table, Message, Spin } from '@arco-design/web-react';
import { Link, useHistory } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { fetchWorkflowList, favourTheWorkFlow } from 'services/workflow';
import styled from './index.module.less';
import i18n from 'i18n';
import { formatTimestamp } from 'shared/date';
import { useTranslation } from 'react-i18next';
import { Workflow, WorkflowState, WorkflowStateFilterParam, WorkflowType } from 'typings/workflow';
import WorkflowStage from '../WorkflowStage';
import WorkflowActions from '../../WorkflowActions';
import WhichProject from 'components/WhichProject';
import MultiSelect from 'components/MultiSelect';
import { workflowStateOptionList } from 'shared/workflow';
import { useUrlState, useTablePaginationWithUrlState, useGetCurrentProjectId } from 'hooks';
import { TIME_INTERVAL } from 'shared/constants';
import { Switch } from '@arco-design/web-react';
import { FilterOp } from 'typings/filter';
import { constructExpressionTree, expression2Filter } from 'shared/filter';

const Row = Grid.Row;
const Col = Grid.Col;

type TableColumnsOptions = {
  onSuccess?: () => void;
  withoutActions?: boolean;
  withoutFavour?: boolean;
  defaultFavourFilteredValue?: string[];
  onForkableChange?: (record: Workflow, val: boolean) => void;
  onFavourSwitchChange?: (record: Workflow) => void;
};

export const getWorkflowTableColumns = (options: TableColumnsOptions = {}) => {
  const ret = [
    {
      title: i18n.t('workflow.name'),
      dataIndex: 'name',
      key: 'name',
      width: 300,
      render: (name: string, record: Workflow) => {
        const { state } = record;
        const { INVALID } = WorkflowState;
        return (
          <>
            <Link
              to={`/workflow-center/workflows/${record.id}`}
              rel="nopener"
              className={styled.col_name_link}
              data-invalid={state === INVALID}
            >
              {name}
            </Link>
            <small className={styled.col_uuid}>uuid: {record.uuid}</small>
          </>
        );
      },
    },
    {
      title: i18n.t('workflow.col_status'),
      dataIndex: 'state',
      width: 150,
      render: (_: string, record: Workflow) => <WorkflowStage workflow={record} />,
    },
    {
      title: i18n.t('workflow.col_project'),
      dataIndex: 'project_id',
      width: 150,
      render: (project_id: number) => <WhichProject id={project_id} />,
    },
    {
      title: i18n.t('workflow.col_date'),
      dataIndex: 'created_at',
      width: 200,
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    },
    {
      title: i18n.t('workflow.col_favorite'),
      dataIndex: 'favour',
      defaultFilteredValue: options.defaultFavourFilteredValue,
      width: 120,
      filters: [
        {
          text: i18n.t('term_favored'),
          value: '1',
        },
        {
          text: i18n.t('term_unfavored'),
          value: '0',
        },
      ],
      filterMultiple: false,
      render(favorite: number, record: Workflow) {
        return (
          <Switch
            size="small"
            onChange={() => options.onFavourSwitchChange?.(record)}
            checked={Boolean(favorite)}
          />
        );
      },
    },
  ];

  if (options.withoutFavour) {
    ret.splice(ret.length - 1, 1);
  }

  if (!options.withoutActions) {
    ret.push({
      title: i18n.t('workflow.col_actions'),
      dataIndex: 'operation',
      width: 400,
      render: (_: any, record: Workflow) => (
        <WorkflowActions onSuccess={options.onSuccess} workflow={record} type="text" size="mini" />
      ),
    });
  }

  return ret;
};

type QueryParams = {
  project?: string;
  keyword?: string;
  uuid?: string;
  states?: WorkflowStateFilterParam[];
  page?: number;
  favour?: '0' | '1';
  system?: string;
};

type TWorkflowListRes = {
  data: Workflow[];
};

type ListProps = {
  type: WorkflowType;
};

export const WORKFLOW_LIST_QUERY_KEY = 'fetchWorkflowList';

const List: FC<ListProps> = ({ type }) => {
  const { t } = useTranslation();
  const [form] = Form.useForm<QueryParams>();
  const history = useHistory();
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    keyword: '',
    uuid: '',
    states: [],
    filter: initFilter(),
    favour: undefined,
  });
  const projectId = useGetCurrentProjectId();

  const { urlState: pageInfoState, paginationProps } = useTablePaginationWithUrlState();

  const initFilterParams = expression2Filter(urlState.filter);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [filterParams, setFilterParams] = useState<QueryParams>({
    states: initFilterParams.states || [],
    keyword: initFilterParams.keyword || '',
    uuid: initFilterParams.uuid || '',
    system: initFilterParams.system || false,
  });

  const queryClient = useQueryClient();
  const listQueryKey = [
    WORKFLOW_LIST_QUERY_KEY,
    urlState.keyword,
    urlState.uuid,
    urlState.states,
    urlState.favour,
    projectId,
    pageInfoState.page,
    pageInfoState.pageSize,
  ];
  const listQuery = useQuery(
    listQueryKey,
    () => {
      if (!projectId) {
        Message.info(t('select_project_notice'));
      }
      return fetchWorkflowList({
        ...urlState,
        project: projectId,
        page: pageInfoState.page,
        pageSize: pageInfoState.pageSize,
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
      keepPreviousData: true,
    },
  );
  const { isLoading, isError, data: res, error, refetch } = listQuery;
  const favourMutation = useMutation(
    async (workflow: Workflow) => {
      await favourTheWorkFlow(projectId ?? 0, workflow.id, !Boolean(workflow.favour));
    },
    {
      onMutate(workflow) {
        // cancel ongoing list queries
        queryClient.cancelQueries(listQueryKey);
        const oldData = queryClient.getQueryData<TWorkflowListRes>(listQueryKey);
        const operatingIndex = oldData?.data.findIndex((item) => item.id === workflow.id);

        if (operatingIndex === -1 || operatingIndex === undefined) {
          return oldData;
        }

        // temporarily update list.
        queryClient.setQueryData<TWorkflowListRes>(listQueryKey, (oldData) => {
          const copied = oldData?.data ? [...oldData.data] : [];
          copied.splice(operatingIndex, 1, {
            ...workflow,
            favour: !workflow.favour,
          });

          return {
            data: copied,
          };
        });

        return oldData;
      },
      onSuccess() {
        refetch();
      },
      onError(_: any, __: any, oldData) {
        // if failed, reverse list data to the old one.
        queryClient.setQueryData(listQueryKey, oldData);
      },
    },
  );

  if (isError && error) {
    Message.error((error as Error).message);
  }

  const workflowListShow = useMemo(() => {
    const workflowList = res?.data ?? [];
    return workflowList;
  }, [res]);

  return (
    <>
      <Row justify="space-between" align="center">
        <Col span={4}>
          {type === WorkflowType.MY ? (
            <Button className={'custom-operation-button'} type="primary" onClick={goCreate}>
              {t('workflow.create_workflow')}
            </Button>
          ) : (
            <></>
          )}
        </Col>
        <Col span={20}>
          <Form
            initialValues={{ ...urlState }}
            layout="inline"
            form={form}
            onChange={onParamsChange}
            style={{ justifyContent: 'flex-end' }}
          >
            <Form.Item field="states" className={styled.workflow_list_form_item}>
              <MultiSelect
                isHideIndex={true}
                placeholder="任务状态"
                optionList={workflowStateOptionList || []}
                onChange={form.submit}
                allowClear
                style={{ minWidth: '227px', maxWidth: '500px', fontSize: '12px' }}
              />
            </Form.Item>
            <Form.Item field="uuid" className={styled.workflow_list_form_item}>
              <Input.Search
                className={'custom-input'}
                placeholder={t('workflow.placeholder_uuid_searchbox')}
                onSearch={form.submit}
                allowClear
              />
            </Form.Item>
            <Form.Item field="keyword" className={styled.workflow_list_form_item}>
              <Input.Search
                className={'custom-input'}
                placeholder={t('workflow.placeholder_name_searchbox')}
                onSearch={form.submit}
                allowClear
              />
            </Form.Item>
          </Form>
        </Col>
      </Row>
      <Spin loading={isLoading}>
        <div className={styled.workflow_list_container}>
          <Table
            className="custom-table custom-table-left-side-filter"
            data={workflowListShow}
            columns={getWorkflowTableColumns({
              onSuccess,
              onFavourSwitchChange: (workflow: Workflow) => favourMutation.mutate(workflow),
              defaultFavourFilteredValue: urlState.favour ? [urlState.favour] : [],
            })}
            onChange={(_, sorter, filter, extra) => {
              if (extra.action === 'filter') {
                setUrlState({
                  page: 1,
                  favour: filter.favour?.[0] ?? undefined,
                });
              }
            }}
            scroll={{ x: '100%' }}
            rowKey="id"
            pagination={{
              ...paginationProps,
              total: listQuery.data?.page_meta?.total_items ?? undefined,
            }}
            style={{ minWidth: '800px' }}
          />
        </div>
      </Spin>
    </>
  );
  function onParamsChange(values: QueryParams) {
    // Set urlState will auto-trigger list query
    setUrlState({ ...values, page: 1 });
  }
  function onSuccess() {
    refetch();
  }

  function goCreate() {
    history.push('/workflow-center/workflows/initiate/basic');
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  function constructFilterArray(value: QueryParams) {
    const expressionNodes = [];
    expressionNodes.push({
      field: 'system',
      op: FilterOp.EQUAL,
      bool_value: type === WorkflowType.SYSTEM,
    });

    const serialization = constructExpressionTree(expressionNodes);
    setFilterParams({
      system: value.system,
    });
    setUrlState((prevState) => ({
      ...prevState,
      filter: serialization,
      page: 1,
    }));
  }

  function initFilter() {
    const expressionNodes = [];
    expressionNodes.push({
      field: 'system',
      op: FilterOp.EQUAL,
      bool_value: type === WorkflowType.SYSTEM,
    });
    return constructExpressionTree(expressionNodes);
  }
};

export default List;
