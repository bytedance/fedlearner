import React, { FC, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Input,
  Message,
  Space,
  Statistic,
  Table,
  TableColumnProps,
  Tabs,
  Tooltip,
  Tag,
  Typography,
} from '@arco-design/web-react';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { formatTimestamp } from 'shared/date';
import {
  Dataset,
  DatasetDataType,
  DatasetDataTypeText,
  DatasetKind,
  DatasetKindLabel,
  DatasetKindLabelCapitalMapper,
  DatasetStateFront,
  DatasetTabType,
  ParticipantDataset,
  DatasetRawPublishStatus,
  DatasetProcessedAuthStatus,
  DatasetProcessedMyAuthStatus,
  ParticipantInfo,
  DatasetKindBackEndType,
  DatasetType__archived,
  DATASET_COPY_CHECKER,
} from 'typings/dataset';
import { useQuery } from 'react-query';
import {
  deleteDataset,
  fetchDatasetList,
  fetchParticipantDatasetList,
  authorizeDataset,
  cancelAuthorizeDataset,
} from 'services/dataset';
import { getTotalDataSize } from 'shared/dataset';
import { noop } from 'lodash-es';
import DatasetActions, { DatasetAction } from '../DatasetActions';
import ImportProgress from '../ImportProgress';
import { Link, Redirect } from 'react-router-dom';
import {
  datasetKindLabelValueMap,
  FILTER_OPERATOR_MAPPER,
  filterExpressionGenerator,
  getSortOrder,
  RawAuthStatusOptions,
  RawPublishStatusOptions,
} from '../../shared';
import { expression2Filter } from 'shared/filter';
import GridRow from 'components/_base/GridRow';
import { generatePath, useHistory, useParams } from 'react-router';
import { humanFileSize } from 'shared/file';
import Modal from 'components/Modal';
import {
  useGetAppFlagValue,
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useGetCurrentProjectType,
  useTablePaginationWithUrlState,
  useUrlState,
  useGetCurrentProjectAbilityConfig,
} from 'hooks';
import { TIME_INTERVAL, CONSTANTS } from 'shared/constants';
import WhichParticipant from 'components/WhichParticipant';
import { ColumnProps } from '@arco-design/web-react/es/Table';
import ExportModal from 'components/DatasetExportModal';
import StatusProgress from 'components/StatusProgress';
import { DatasetDetailSubTabs } from '../../DatasetDetail';
import { IconPlus } from '@arco-design/web-react/icon';
import { transformRegexSpecChar } from 'shared/helpers';
import DatasetPublishAndRevokeModal from 'components/DatasetPublishAndRevokeModal';
import { ParticipantType } from 'typings/participant';
import { PageMeta } from 'typings/app';
import { PaginationProps } from '@arco-design/web-react/es/Pagination/pagination';
import { SorterResult } from '@arco-design/web-react/es/Table/interface';
import { FlagKey } from 'typings/flag';
import { fetchSysInfo } from 'services/settings';
import { FilterOp } from 'typings/filter';
import './index.less';

const { Text } = Typography;

type ColumnsGetterOptions = {
  onDeleteClick?: any;
  onPublishClick: (dataset: Dataset) => void;
  onExportClick: (dataset: Dataset) => void;
  onAuthorize: (dataset: Dataset) => void;
  onCancelAuthorize: (dataset: Dataset) => void;
  onSuccess?: any;
  withoutActions?: boolean;
};

type TableFilterConfig = Pick<TableColumnProps, 'filters' | 'onFilter'>;

const FILTER_OPERATOR_MAPPER_List = {
  ...FILTER_OPERATOR_MAPPER,
  dataset_kind: FilterOp.IN,
};

/**
 * table columns generator
 * TODO: there are too many 「if-else」 and need to chore
 * @param projectId
 * @param tab
 * @param kindLabel
 * @param options callback of operation
 * @param bcsSupportEnabled Whether to access blockchain
 */
export const getDatasetTableColumns = (
  projectId: ID | undefined,
  tab: DatasetTabType | undefined,
  kindLabel: DatasetKindLabel,
  options: ColumnsGetterOptions,
  urlState: Partial<{
    page: number;
    pageSize: number;
    filter: string;
    order_by: string;
    state_frontend: DatasetStateFront[];
  }>,
  datasetParticipantFilters: TableFilterConfig,
  myPureDomainName: string,
  bcsSupportEnabled: boolean,
  reviewCenterConfiguration: string,
) => {
  const onPerformAction = (payload: { action: DatasetAction; dataset: Dataset }) => {
    return {
      delete: options.onDeleteClick,
      'publish-to-project': options.onPublishClick,
      export: options.onExportClick,
      authorize: options.onAuthorize,
      'cancel-authorize': options.onCancelAuthorize,
    }[payload.action](payload.dataset);
  };
  const renderStatistic = (val: number | string) => {
    return typeof val === 'number' ? (
      <Statistic
        groupSeparator={true}
        styleValue={{ fontSize: '12px', fontWeight: 400 }}
        value={val}
      />
    ) : (
      '-'
    );
  };

  const renderParticipantAuth = (val: ParticipantInfo[]) => {
    return (
      <>
        {val.map((participant, index) => (
          <div key={index}>
            {participant.name}{' '}
            {participant.auth_status === DatasetProcessedMyAuthStatus.AUTHORIZED
              ? '已授权'
              : '未授权'}
          </div>
        ))}
      </>
    );
  };

  const getPublishStatusFilters = () => {
    if (reviewCenterConfiguration === '{}') {
      return [
        {
          text: '未发布',
          value: DatasetRawPublishStatus.UNPUBLISHED,
        },
        {
          text: '已发布',
          value: DatasetRawPublishStatus.PUBLISHED,
        },
      ];
    }
    return [
      {
        text: '未发布',
        value: DatasetRawPublishStatus.UNPUBLISHED,
      },
      {
        text: '待审批',
        value: DatasetRawPublishStatus.TICKET_PENDING,
      },
      {
        text: '审批拒绝',
        value: DatasetRawPublishStatus.TICKET_DECLINED,
      },
      {
        text: '已发布',
        value: DatasetRawPublishStatus.PUBLISHED,
      },
    ];
  };

  const cols: ColumnProps[] = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 240,
      render: (name: string, record: Dataset) => {
        const to = `/datasets/${kindLabel}/detail/${record.id}/${DatasetDetailSubTabs.DatasetJobDetail}`;
        if (record.dataset_type === DatasetType__archived.STREAMING) {
          return (
            <>
              <Tooltip
                content={
                  <Text style={{ color: '#fff' }} copyable>
                    {name}
                  </Text>
                }
              >
                {tab === DatasetTabType.PARTICIPANT ? (
                  <span className="dataset_list_name">{name}</span>
                ) : (
                  <Link className="dataset_list_name" to={to}>
                    {name}
                  </Link>
                )}
              </Tooltip>
              <Tag color="blue" size="small">
                增量
              </Tag>
            </>
          );
        } else {
          return tab === DatasetTabType.PARTICIPANT ? name : <Link to={to}>{name}</Link>;
        }
      },
    },
    tab === DatasetTabType.PARTICIPANT
      ? {
          title: '合作伙伴名称',
          dataIndex: 'participant_id',
          width: 180,
          ...datasetParticipantFilters,
          filteredValue: expression2Filter(urlState.filter!).participant_id,
          render(id) {
            return <WhichParticipant id={id} />;
          },
        }
      : {
          title: '数据集状态',
          dataIndex: 'state_frontend',
          width: 180,
          filters: [
            {
              text: '待处理',
              value: DatasetStateFront.PENDING,
            },
            {
              text: '处理中',
              value: DatasetStateFront.PROCESSING,
            },
            {
              text: '可用',
              value: DatasetStateFront.SUCCEEDED,
            },
            {
              text: '处理失败',
              value: DatasetStateFront.FAILED,
            },
            {
              text: '删除中',
              value: DatasetStateFront.DELETING,
            },
          ],
          filteredValue: urlState.state_frontend,
          render: (_: any, record: Dataset) => {
            return <ImportProgress dataset={record} />;
          },
        },
    {
      title: '数据格式',
      dataIndex: tab === DatasetTabType.PARTICIPANT ? 'format' : 'dataset_format',
      width: 150,
      filters: [
        { text: DatasetDataTypeText.STRUCT, value: DatasetDataType.STRUCT },
        { text: DatasetDataTypeText.PICTURE, value: DatasetDataType.PICTURE },
      ],
      // Return different values depending on whether the tab is PARTICIPANT
      onFilter: (value: string, record: any) => {
        if (tab === DatasetTabType.PARTICIPANT) {
          return (
            record?.[tab === DatasetTabType.PARTICIPANT ? 'format' : 'dataset_format'] === value
          );
        }
        return true;
      },
      filteredValue: expression2Filter(urlState.filter!)[
        tab === DatasetTabType.PARTICIPANT ? 'format' : 'dataset_format'
      ],
      render(val: DatasetDataType) {
        switch (val) {
          case DatasetDataType.STRUCT:
            return DatasetDataTypeText.STRUCT;
          case DatasetDataType.PICTURE:
            return DatasetDataTypeText.PICTURE;
          case DatasetDataType.NONE_STRUCTURED:
            return DatasetDataTypeText.NONE_STRUCTURED;
        }
      },
    },
    {
      title: (
        <Space>
          <span>数据大小</span>
          <Tooltip content="数据以系统格式存储的大小，较源文件会有一定变化">
            <IconInfoCircle style={{ color: 'var(--color-text-3)', fontSize: 14 }} />
          </Tooltip>
        </Space>
      ),
      dataIndex: 'file_size',
      width: 180,
      render: (file_size: number, record: Dataset) => {
        const isInternalProcessed =
          record.dataset_kind === DatasetKindBackEndType.INTERNAL_PROCESSED;
        const isErrorFileSize = file_size === -1;
        if (isErrorFileSize) {
          return '异常';
        }
        return <span>{isInternalProcessed ? '-' : humanFileSize(getTotalDataSize(record))}</span>;
      },
    },
  ];

  if (tab === DatasetTabType.MY) {
    cols.push({
      title: '数据集样本量',
      dataIndex: 'num_example',
      width: 180,
      render: (num: number, record: Dataset) => {
        const isInternalProcessed =
          record.dataset_kind === DatasetKindBackEndType.INTERNAL_PROCESSED;
        const isNoCopy = record.import_type === DATASET_COPY_CHECKER.NONE_COPY;
        const isErrorFileSize = record.file_size === -1;
        if (isErrorFileSize) {
          return '异常';
        }
        return renderStatistic(isInternalProcessed || isNoCopy ? '' : num);
      },
    });

    if (kindLabel === DatasetKindLabel.RAW) {
      if (bcsSupportEnabled) {
        cols.push({
          title: '数据价值',
          dataIndex: 'total_value',
          width: 180,
          render: renderStatistic,
        });
      }
      cols.push(
        {
          title: '创建者',
          dataIndex: 'creator_username',
          key: 'creator_username',
          width: 100,
          render(val: string) {
            return val || CONSTANTS.EMPTY_PLACEHOLDER;
          },
        },
        {
          title: '发布状态',
          dataIndex: 'publish_frontend_state',
          width: 150,
          filters: getPublishStatusFilters(),
          onFilter: (value: string, record: Dataset) => {
            return value === record.publish_frontend_state;
          },
          filterMultiple: false,
          filteredValue: expression2Filter(urlState.filter!).publish_frontend_state
            ? [expression2Filter(urlState.filter!).publish_frontend_state]
            : [],
          render: (publish_frontend_state: DatasetRawPublishStatus) => {
            return (
              <StatusProgress options={RawPublishStatusOptions} status={publish_frontend_state} />
            );
          },
        },
        {
          title: '创建时间',
          dataIndex: 'created_at',
          width: 180,
          sortOrder: getSortOrder(urlState, 'created_at'),
          sorter(a: Dataset, b: Dataset) {
            return a.created_at - b.created_at;
          },
          render: (date: number) => <div>{formatTimestamp(date)}</div>,
        },
      );
    } else {
      cols.push(
        {
          title: '创建者',
          dataIndex: 'creator_username',
          key: 'creator_username',
          width: 100,
          render(val: string) {
            return val || CONSTANTS.EMPTY_PLACEHOLDER;
          },
        },
        {
          title: '授权状态',
          dataIndex: 'auth_frontend_state',
          width: 150,
          render: (auth_frontend_state: DatasetProcessedAuthStatus, record: Dataset) => {
            // 处于待授权状态时展示hover
            if (auth_frontend_state === DatasetProcessedAuthStatus.AUTH_PENDING) {
              const participants_info = Object.entries(
                record.participants_info.participants_map,
              ).map(([key, value]) => ({
                name: key === myPureDomainName ? '我方' : key,
                auth_status: value['auth_status'],
              }));
              return (
                <StatusProgress
                  options={RawAuthStatusOptions}
                  status={auth_frontend_state || DatasetProcessedAuthStatus.AUTH_PENDING}
                  isTip={true}
                  toolTipContent={renderParticipantAuth(participants_info || [])}
                />
              );
            }
            return (
              <StatusProgress
                options={RawAuthStatusOptions}
                status={auth_frontend_state || DatasetProcessedAuthStatus.TICKET_PENDING}
              />
            );
          },
        },
        {
          title: '创建时间',
          dataIndex: 'created_at',
          width: 180,
          sortOrder: getSortOrder(urlState, 'created_at'),
          sorter(a: Dataset, b: Dataset) {
            return a.created_at - b.created_at;
          },
          render: (date: number) => <div>{formatTimestamp(date)}</div>,
        },
      );
    }
  }

  if (tab === DatasetTabType.PARTICIPANT) {
    if (bcsSupportEnabled) {
      cols.push({
        title: '使用单价',
        dataIndex: 'value',
        width: 180,
        sortOrder: getSortOrder(urlState, 'value'),
        sorter(a: ParticipantDataset, b: ParticipantDataset) {
          return (a.value || 0) - (b.value || 0);
        },
        render: renderStatistic,
      });
    }
    cols.push({
      title: '最近更新',
      dataIndex: 'updated_at',
      width: 200,
      sortOrder: getSortOrder(urlState, 'updated_at'),
      sorter(a: ParticipantDataset, b: ParticipantDataset) {
        return a.updated_at - b.updated_at;
      },
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
    });
  }

  if (!options.withoutActions && tab === DatasetTabType.MY) {
    cols.push({
      title: '操作',
      dataIndex: 'operation',
      name: 'operation',
      fixed: 'right',
      width: 200,
      render: (_: number, record: Dataset) => (
        <DatasetActions
          onPerformAction={onPerformAction}
          dataset={record}
          type="text"
          kindLabel={kindLabel}
        />
      ),
    } as any);
  }

  return cols;
};

export const DATASET_LIST_QUERY_KEY = 'fetchDatasetList';

export const GlobalDatasetIdToErrorMessageMapContext = React.createContext<{
  [key: number]: string;
}>({});

type Props = {
  dataset_kind: DatasetKind;
};

const DatasetListTable: FC<Props> = ({ dataset_kind }) => {
  const { kind_label, tab } = useParams<{
    kind_label: DatasetKindLabel;
    tab?: DatasetTabType;
  }>();
  const isProcessedDataset = kind_label === DatasetKindLabel.PROCESSED;
  const history = useHistory();
  const projectId = useGetCurrentProjectId();
  const projectType = useGetCurrentProjectType();
  const participantList = useGetCurrentProjectParticipantList();
  const { hasTrusted } = useGetCurrentProjectAbilityConfig();
  const [currentExportId, setCurrentExportId] = useState<ID>();
  const [isShowExportModal, setIsShowExportModal] = useState(false);
  const [isShowPublishModal, setIsShowPublishModal] = useState(false);
  const [total, setTotal] = useState(0);
  const [pageTotal, setPageTotal] = useState(0);
  const [selectDataset, setSelectDataset] = useState<Dataset>();
  const [datasetIdToErrorMessageMap, setDatasetIdToErrorMessageMap] = useState<{
    [key: number]: string;
  }>({});
  const [urlState, setUrlState] = useUrlState<any>({
    page: 1,
    pageSize: 10,
    filter: filterExpressionGenerator(
      {
        dataset_kind:
          kind_label === DatasetKindLabel.RAW
            ? [DatasetKindLabelCapitalMapper[kind_label]]
            : [
                DatasetKindLabelCapitalMapper[kind_label],
                DatasetKindBackEndType.INTERNAL_PROCESSED,
              ],
        project_id: projectId,
        auth_status: isProcessedDataset
          ? [DatasetProcessedMyAuthStatus.AUTHORIZED, DatasetProcessedMyAuthStatus.WITHDRAW]
          : undefined,
      },
      FILTER_OPERATOR_MAPPER_List,
    ),
    order_by: '',
  });
  const { paginationProps } = useTablePaginationWithUrlState();
  const bcs_support_enabled = useGetAppFlagValue(FlagKey.BCS_SUPPORT_ENABLED);
  const review_center_configuration = useGetAppFlagValue(FlagKey.REVIEW_CENTER_CONFIGURATION);
  const isLightClient = projectType === ParticipantType.LIGHT_CLIENT;
  const sysInfoQuery = useQuery(['fetchSysInfo'], () => fetchSysInfo(), {
    retry: 2,
    refetchOnWindowFocus: false,
    enabled: Boolean(isProcessedDataset),
  });

  const myPureDomainName = useMemo<string>(() => {
    return sysInfoQuery.data?.data?.pure_domain_name ?? '';
  }, [sysInfoQuery.data]);
  const listQuery = useQuery<{
    data: Array<Dataset | ParticipantDataset>;
    page_meta?: PageMeta;
  }>(
    [
      DATASET_LIST_QUERY_KEY,
      tab === DatasetTabType.MY ? urlState : null,
      projectId,
      kind_label,
      tab,
    ],
    () => {
      if (!projectId!) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] });
      }

      if (!tab || tab === DatasetTabType.MY) {
        return fetchDatasetList({
          page: urlState.page,
          page_size: urlState.pageSize,
          filter: urlState.filter,
          state_frontend: urlState.state_frontend,
          // when order_by is empty and set order_by = 'created_at desc' default
          order_by: urlState.order_by || 'created_at desc',
        });
      }
      return fetchParticipantDatasetList(projectId!, {
        page: urlState.page,
        page_size: urlState.pageSize,
        kind: DatasetKindLabel.RAW,
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
      keepPreviousData: true,
      refetchOnWindowFocus: false,
    },
  );

  const datasetParticipantFilters: TableFilterConfig = useMemo(() => {
    let filters: { text: string; value: any }[] = [];
    if (Array.isArray(participantList) && participantList.length) {
      filters = participantList.map((item) => ({
        text: item.name,
        value: '' + item.id,
      }));
    }
    return {
      filters,
      onFilter: (value: string, record: ParticipantDataset) => {
        return value === '' + record.participant_id;
      },
    };
  }, [participantList]);

  const list = useMemo(() => {
    if (!listQuery.data?.data) return [];

    let list = listQuery.data.data || [];
    // Because participant_datasets api don't support search by name, we need to filter by web
    if (tab === DatasetTabType.PARTICIPANT) {
      const { name, format, participant_id } = expression2Filter(urlState.filter);
      if (name) {
        const regx = new RegExp(`^.*${transformRegexSpecChar(name)}.*$`); // support fuzzy matching
        list = list.filter((item) => regx.test(item.name));
      }
      if (format) {
        list = list.filter((item: any) => format.includes(item.format));
      }
      if (participant_id) {
        list = list.filter((item: any) => participant_id.includes(String(item.participant_id)));
      }
      setTotal(list.length);
      setPageTotal(Math.ceil(list.length / paginationProps.pageSize));
    } else {
      const { page_meta, data = [] } = listQuery.data;
      setTotal(page_meta?.total_items ?? data.length);
      setPageTotal(page_meta?.total_pages ?? Math.ceil(data.length / paginationProps.pageSize));
    }

    return list;
  }, [listQuery.data, urlState.filter, tab, paginationProps.pageSize]);

  const pagination = useMemo(() => {
    return pageTotal <= 1
      ? false
      : {
          ...paginationProps,
          total,
        };
  }, [paginationProps, pageTotal, total]);

  const kindLabel = datasetKindLabelValueMap[dataset_kind];
  // 有可信分析能力不展示结果数据创建按钮
  const isHideCreateBtn = hasTrusted && kind_label === DatasetKindLabel.PROCESSED;

  useEffect(() => {
    setUrlState({
      ...urlState,
      filter: filterExpressionGenerator(
        {
          ...expression2Filter(urlState.filter),
          project_id: projectId,
        },
        FILTER_OPERATOR_MAPPER_List,
      ),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  return (
    <>
      <GridRow justify="space-between" align="center">
        <Space>
          {!isHideCreateBtn && (
            <Button
              className={'custom-operation-button'}
              type="primary"
              onClick={goCreateDataset}
              icon={<IconPlus />}
            >
              创建数据集
            </Button>
          )}
          {kind_label !== DatasetKindLabel.PROCESSED && (
            <Tabs
              className="custom-tabs"
              type="text"
              defaultActiveTab={tab ?? DatasetTabType.MY}
              onChange={onTabChange}
            >
              {Object.entries(DatasetTabType).map((item) => {
                const [, value] = item;
                const title = value === DatasetTabType.MY ? '我方数据集' : '合作伙伴数据集';
                return (
                  <Tabs.TabPane
                    disabled={isLightClient && value === DatasetTabType.PARTICIPANT}
                    key={value}
                    title={title}
                  />
                );
              })}
            </Tabs>
          )}
        </Space>
        <Space>
          <Input.Search
            className={'custom-input'}
            placeholder="输入数据集名称搜索"
            defaultValue={expression2Filter(urlState.filter).name}
            onSearch={onSearch}
            onClear={() => onSearch('')}
            allowClear
          />
        </Space>
      </GridRow>
      <GlobalDatasetIdToErrorMessageMapContext.Provider value={datasetIdToErrorMessageMap}>
        <Table
          className={'custom-table custom-table-left-side-filter'}
          loading={listQuery.isFetching}
          data={list || []}
          scroll={{ x: '100%' }}
          columns={getDatasetTableColumns(
            projectId,
            tab,
            kindLabel,
            {
              onSuccess: noop,
              onDeleteClick,
              onPublishClick,
              onExportClick,
              onAuthorize,
              onCancelAuthorize,
            },
            urlState,
            datasetParticipantFilters,
            myPureDomainName,
            bcs_support_enabled as boolean,
            review_center_configuration as string,
          )}
          rowKey="uuid"
          pagination={pagination}
          onChange={onTableChange}
        />
      </GlobalDatasetIdToErrorMessageMapContext.Provider>
      {!tab ? (
        <Redirect
          to={generatePath('/datasets/:kind_label/:tab', {
            kind_label,
            tab: DatasetTabType.MY,
          })}
        />
      ) : null}

      <ExportModal
        id={currentExportId}
        visible={isShowExportModal}
        onCancel={onExportModalClose}
        onSuccess={onExportSuccess}
      />

      <DatasetPublishAndRevokeModal
        onCancel={onPublishCancel}
        onSuccess={onPublishSuccess}
        dataset={selectDataset}
        visible={isShowPublishModal}
      />
    </>
  );

  function goCreateDataset() {
    // 统一在路由区分新旧数据集入口
    history.push(`/datasets/${kindLabel}/create`);
  }

  function onSearch(value: string) {
    const filters = expression2Filter(urlState.filter);
    filters.name = value;
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
      filter: filterExpressionGenerator(filters, FILTER_OPERATOR_MAPPER_List),
    }));
  }

  function onTabChange(tab: string) {
    history.push(
      generatePath('/datasets/:kind_label/:tab', {
        kind_label,
        tab,
      }),
    );
  }

  function onDeleteClick(dataset: Dataset) {
    Modal.delete({
      title: '确定要删除吗？',
      content: '删除操作无法恢复，请谨慎操作',
      onOk: async () => {
        try {
          const resp = await deleteDataset(dataset.id);
          // If delete success, HTTP response status code is 204, resp is empty string
          const isDeleteSuccess = !resp;
          if (isDeleteSuccess) {
            Message.success('删除成功');
            listQuery.refetch();
            setDatasetIdToErrorMessageMap((prevState) => {
              const copyState = { ...prevState };
              delete copyState[dataset.id as number];
              return copyState;
            });
          } else {
            const errorMessage = resp?.message ?? '删除失败';
            Message.error(errorMessage!);
            setDatasetIdToErrorMessageMap((prevState) => ({
              ...prevState,
              [dataset.id]: errorMessage,
            }));
          }
        } catch (error) {
          Message.error(error.message);
        }
      },
    });
  }

  function onTableChange(
    pagination: PaginationProps,
    sorter: SorterResult,
    filters: Partial<Record<keyof Dataset | keyof ParticipantDataset, string[]>>,
    extra: {
      currentData: Array<Dataset | ParticipantDataset>;
      action: 'paginate' | 'sort' | 'filter';
    },
  ) {
    switch (extra.action) {
      case 'filter':
        const filtersCopy = {
          ...filters,
          name: expression2Filter(urlState.filter).name,
          project_id: projectId,
          dataset_kind:
            kind_label === DatasetKindLabel.RAW
              ? [DatasetKindLabelCapitalMapper[kind_label]]
              : [
                  DatasetKindLabelCapitalMapper[kind_label],
                  DatasetKindBackEndType.INTERNAL_PROCESSED,
                ], // 可信中心的结果数据集也进行展示
          publish_frontend_state: filters.publish_frontend_state?.[0] ?? undefined,
        };
        setUrlState((prevState) => ({
          ...prevState,
          page: 1,
          filter: filterExpressionGenerator(filtersCopy, FILTER_OPERATOR_MAPPER_List),
          state_frontend: filtersCopy.state_frontend ?? undefined,
        }));
        break;
      case 'sort':
        let orderValue = '';
        if (sorter.direction) {
          orderValue = sorter.direction === 'ascend' ? 'asc' : 'desc';
        }
        setUrlState((prevState) => ({
          ...prevState,
          order_by: orderValue ? `${sorter.field} ${orderValue}` : '',
        }));
        break;
      default:
        break;
    }
  }

  function onPublishClick(dataset: Dataset) {
    setSelectDataset(dataset);
    setIsShowPublishModal(true);
  }
  function onPublishSuccess() {
    setIsShowPublishModal(false);
    listQuery.refetch();
  }
  function onPublishCancel() {
    setIsShowPublishModal(false);
  }
  async function onAuthorize(dataset: Dataset) {
    try {
      await authorizeDataset(dataset.id);
      listQuery.refetch();
    } catch (err: any) {
      Message.error(err.message);
    }
  }

  async function onCancelAuthorize(dataset: Dataset) {
    try {
      await cancelAuthorizeDataset(dataset.id);
      listQuery.refetch();
    } catch (err: any) {
      Message.error(err.message);
    }
  }
  function onExportClick(dataset: Dataset) {
    setCurrentExportId(dataset.id);
    setIsShowExportModal(true);
  }
  function onExportSuccess(datasetId: ID, datasetJobId: ID) {
    onExportModalClose();
    if (!datasetJobId && datasetJobId !== 0) {
      Message.info('导出任务ID缺失，请手动跳转「任务管理」查看详情');
    } else {
      history.push(`/datasets/${datasetId}/new/job_detail/${datasetJobId}`);
    }
  }
  function onExportModalClose() {
    setCurrentExportId(undefined);
    setIsShowExportModal(false);
  }
};

export default DatasetListTable;
