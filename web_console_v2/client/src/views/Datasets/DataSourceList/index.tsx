import React, { FC, useMemo, useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { uniqBy } from 'lodash-es';

import { useGetCurrentProjectId, useTablePaginationWithUrlState, useUrlState } from 'hooks';

import { TIME_INTERVAL } from 'shared/constants';
import { formatTimestamp } from 'shared/date';
import { transformRegexSpecChar } from 'shared/helpers';
import { CONSTANTS } from 'shared/constants';
import { useHistory, generatePath } from 'react-router';
import routes from '../routes';
import { Link } from 'react-router-dom';
import { fetchDataSourceList, deleteDataSource } from 'services/dataset';

import { Button, Input, Message, Table, Tag, Tooltip, Typography } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout from 'components/SharedPageLayout';
import MoreActions from 'components/MoreActions';
import Modal from 'components/Modal';
import { IconPlus } from '@arco-design/web-react/icon';

import { ColumnProps } from '@arco-design/web-react/es/Table';
import { DataSource, DatasetType, DataSourceDataType } from 'typings/dataset';
import { DataSourceDetailSubTabs } from 'views/Datasets/DataSourceDetail';
import styled from './index.module.less';

const { Text } = Typography;

type TProps = {};
const { Search } = Input;

const List: FC<TProps> = function (props: TProps) {
  const history = useHistory();
  // const [isEdit, setIsEdit] = useState(false);
  // const [selectedData, setSelectedData] = useState<DataSource>();
  const [pageTotal, setPageTotal] = useState(0);
  const [urlState, setUrlState] = useUrlState({
    keyword: '',
    types: [],
    created_at_sort: '',
  });
  const { paginationProps } = useTablePaginationWithUrlState();

  const projectId = useGetCurrentProjectId();

  const listQuery = useQuery(
    ['fetchDataSourceList', projectId],
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: [] });
      }
      return fetchDataSourceList({
        projectId,
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST,
      refetchOnWindowFocus: false,
    },
  );

  const deleteMutation = useMutation(
    (dataSourceId: ID) => {
      return deleteDataSource(dataSourceId);
    },
    {
      onSuccess() {
        listQuery.refetch();
        Message.success('删除成功');
      },
      onError(e: any) {
        Message.error(e.message);
      },
    },
  );

  const list = useMemo(() => {
    if (!listQuery.data?.data) return [];

    let list = listQuery.data.data;

    if (urlState.keyword) {
      const regx = new RegExp(`^.*${transformRegexSpecChar(urlState.keyword)}.*$`); // support fuzzy matching
      list = list.filter((item) => regx.test(item.name));
    }
    setPageTotal(Math.ceil(list.length / paginationProps.pageSize));
    return list;
  }, [listQuery.data, urlState.keyword, paginationProps.pageSize]);

  const typeFilters = useMemo(() => {
    if (!listQuery.data?.data) return [];

    const list = listQuery.data.data || [];

    return {
      filters: uniqBy(list, 'type').map((item) => {
        return { text: item.type, value: item.type };
      }),
      onFilter: (value: string, record: DataSource) => {
        return record?.type === value;
      },
    };
  }, [listQuery.data]);

  const columns = useMemo<ColumnProps<DataSource>[]>(() => {
    return [
      {
        title: '名称',
        dataIndex: 'name',
        width: 200,
        render: (value: any, record: any) => {
          const to = `/datasets/data_source/${record.id}/${DataSourceDetailSubTabs.PreviewFile}`;
          if (record.dataset_type === DatasetType.STREAMING) {
            return (
              <>
                <Tooltip
                  content={
                    <Text style={{ color: '#fff' }} copyable>
                      {value}
                    </Text>
                  }
                >
                  <Link to={to} className={styled.data_source_name}>
                    {value}
                  </Link>
                </Tooltip>
                <Tag color="blue" size="small">
                  增量
                </Tag>
              </>
            );
          }
          return <Link to={to}>{value}</Link>;
        },
      },
      {
        title: '类型',
        dataIndex: 'type',
        width: 100,
        ...typeFilters,
        defaultFilters: urlState.types ?? [],
        render: (value: any) => value ?? CONSTANTS.EMPTY_PLACEHOLDER,
      },
      {
        title: '数据来源',
        dataIndex: 'url',
        width: 200,
      },
      {
        title: '创建时间',
        dataIndex: 'created_at',
        width: 150,
        sorter(a: DataSource, b: DataSource) {
          return a.created_at - b.created_at;
        },
        defaultSortOrder: urlState?.created_at_sort,
        render: (date: number) => <div>{formatTimestamp(date)}</div>,
      },
      {
        title: '格式',
        dataIndex: 'dataset_format',
        width: 150,
        render: (value: any, record: any) => {
          switch (value) {
            case DataSourceDataType.STRUCT:
              return record.store_format ? `结构化数据/${record.store_format}` : '结构化数据';
            case DataSourceDataType.NONE_STRUCTURED:
              return '非结构化数据';
            case DataSourceDataType.PICTURE:
              return '图片';
            default:
              return '未知';
          }
        },
      },
      {
        title: '操作',
        dataIndex: 'operation',
        fixed: 'right',
        width: 100,
        render: (_: any, record) => (
          <>
            <button
              className="custom-text-button"
              style={{ marginRight: 10 }}
              onClick={() => {
                onEditButtonClick(record);
              }}
              // No support for edit data source now
              disabled={true}
            >
              编辑
            </button>
            <MoreActions
              actionList={[
                {
                  label: '删除',
                  danger: true,
                  onClick() {
                    Modal.delete({
                      title: `确认要删除「${record.name}」？`,
                      content: '删除后，当该数据源将无法恢复，请谨慎操作。',
                      onOk() {
                        deleteMutation.mutate(record.id);
                      },
                    });
                  },
                },
              ]}
            />
          </>
        ),
      },
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlState, typeFilters]);

  const pagination = useMemo(() => {
    return pageTotal <= 1
      ? false
      : {
          ...paginationProps,
        };
  }, [paginationProps, pageTotal]);

  return (
    <SharedPageLayout
      title="数据源"
      tip="数据源指数据的来源，创建数据源即定义访问数据存储空间的地址"
    >
      <GridRow justify="space-between" align="center">
        <Button
          className={'custom-operation-button'}
          type="primary"
          onClick={onCreateButtonClick}
          icon={<IconPlus />}
        >
          添加数据源
        </Button>
        <Search
          className={'custom-input'}
          allowClear
          placeholder="输入数据源名称"
          defaultValue={urlState.keyword}
          onSearch={onSearch}
          onClear={() => onSearch('')}
        />
      </GridRow>
      <Table
        className="custom-table custom-table-left-side-filter"
        rowKey="id"
        loading={listQuery.isFetching}
        data={list}
        scroll={{ x: '100%' }}
        columns={columns}
        pagination={pagination}
        onChange={(pagination, sorter, filters, extra) => {
          switch (extra.action) {
            case 'sort':
              setUrlState((prevState) => ({
                ...prevState,
                [`${sorter.field}_sort`]: sorter.direction,
              }));
              break;
            case 'filter':
              setUrlState((prevState) => ({
                ...prevState,
                page: 1,
                types: filters?.type ?? [],
              }));
              break;
            default:
          }
        }}
      />
    </SharedPageLayout>
  );

  function onCreateButtonClick() {
    history.push(
      generatePath(routes.DatasetCreate, {
        action: 'create',
      }),
    );
  }
  function onEditButtonClick(selectedDataSource: DataSource) {
    // setSelectedData(selectedDataSource);
    // setIsEdit(true);
  }

  function onSearch(value: string) {
    setUrlState((prevState) => ({
      ...prevState,
      keyword: value,
      page: 1,
    }));
  }
};

export default List;
