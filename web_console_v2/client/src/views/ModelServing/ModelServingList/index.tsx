import React, { FC, useMemo } from 'react';
import { useHistory } from 'react-router';

import { useQuery } from 'react-query';
import { fetchModelServingList_new, deleteModelServing_new } from 'services/modelServing';

import { forceToRefreshQuery } from 'shared/queryClient';
import { useGetCurrentProjectId } from 'hooks';

import { useUrlState, useTablePaginationWithUrlState } from 'hooks';
import { TIME_INTERVAL } from 'shared/constants';
import { expression2Filter } from 'shared/filter';

import { Button, Input, Message, Space } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout from 'components/SharedPageLayout';
import Modal from 'components/Modal';
import TodoPopover from 'components/TodoPopover';
import { debounce } from 'lodash-es';

import ModelServingTable from '../ModelServingTable';

import {
  updateServiceInstanceNum,
  getTableFilterValue,
  FILTER_SERVING_OPERATOR_MAPPER,
} from '../shared';

import { ModelServing, ModelServingState } from 'typings/modelServing';
import { SortDirection, SorterResult } from '@arco-design/web-react/es/Table/interface';

import { filterExpressionGenerator } from 'views/Datasets/shared';

import styles from './index.module.less';

const { Search } = Input;

const ModelServingList: FC = () => {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();
  const [urlState, setUrlState] = useUrlState<Record<string, string | undefined>>({
    filter: '',
    order_by: '',
  });
  const { paginationProps } = useTablePaginationWithUrlState();

  const queryKey = ['fetchModelServingList', urlState.filter, urlState.order_by, projectId];

  const listQuery = useQuery(
    queryKey,
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchModelServingList_new(projectId!, {
        filter: urlState.filter,
        order_by: urlState.order_by || 'created_at desc',
      });
    },
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
    },
  );

  const tableDataSource = useMemo(() => {
    if (!listQuery.data) {
      return [];
    }
    return (listQuery.data.data || []).filter(
      (item) =>
        item.status !== ModelServingState.WAITING_CONFIG &&
        (!urlState.status || urlState.status.includes(item.status)) &&
        (!urlState.is_local || urlState.is_local.includes(item.is_local)),
    );
  }, [listQuery.data, urlState]);

  const sorterProps = useMemo<Record<string, SortDirection>>(() => {
    if (urlState.order_by) {
      const order = urlState.order_by?.split(' ') || [];
      return {
        [order[0]]: order?.[1] === 'asc' ? 'ascend' : 'descend',
      };
    }

    return {};
  }, [urlState.order_by]);

  const pagination = useMemo(() => {
    return tableDataSource.length <= paginationProps.pageSize
      ? false
      : {
          ...paginationProps,
          total: tableDataSource.length,
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tableDataSource]);

  return (
    <SharedPageLayout title="在线服务">
      <GridRow justify="space-between" align="center">
        <Button className={'custom-operation-button'} type="primary" onClick={onCreateClick}>
          创建服务
        </Button>

        <Space>
          <Search
            className={`custom-input ${styles.search_content}`}
            allowClear
            defaultValue={expression2Filter(urlState.filter).keyword}
            onChange={debounce(onSearch, 300)}
            placeholder="请输入名称查询"
          />
          <TodoPopover.ModelServing />
        </Space>
      </GridRow>
      <ModelServingTable
        filter={{
          is_local: getTableFilterValue(urlState.is_local),
          status: getTableFilterValue(urlState.status),
        }}
        sorter={sorterProps}
        loading={listQuery.isFetching}
        dataSource={tableDataSource}
        total={listQuery.data?.page_meta?.total_items ?? undefined}
        onRowClick={onRowClick}
        onEditClick={onEditClick}
        onScaleClick={onScaleClick}
        onDeleteClick={onDeleteClick}
        onFilterChange={onFilter}
        onSortChange={onSort}
        pagination={pagination}
      />
    </SharedPageLayout>
  );

  function onSearch(
    value: string,
    event?:
      | React.ChangeEvent<HTMLInputElement>
      | React.MouseEvent<HTMLElement>
      | React.KeyboardEvent<HTMLInputElement>,
  ) {
    const filters = expression2Filter(urlState.filter);
    filters.keyword = value;
    if (!value) {
      setUrlState((prevState) => ({
        ...prevState,
        filter: filterExpressionGenerator(filters, FILTER_SERVING_OPERATOR_MAPPER),
      }));
      return;
    }
    setUrlState((prevState) => ({
      ...prevState,
      filter: filterExpressionGenerator(filters, FILTER_SERVING_OPERATOR_MAPPER),
      page: 1,
    }));
  }

  function onCreateClick() {
    history.push('/model-serving/create');
  }
  function onRowClick(record: ModelServing) {
    history.push(`/model-serving/detail/${record.id}`);
  }
  async function onEditClick(record: ModelServing) {
    history.push(`/model-serving/edit/${record.id}`);
  }
  async function onScaleClick(record: ModelServing) {
    updateServiceInstanceNum(record, () => {
      forceToRefreshQuery([...queryKey]);
    });
  }
  function onDeleteClick(record: ModelServing) {
    if (!projectId) {
      Message.info('请选择工作区！');
      return;
    }
    Modal.delete({
      title: `确认要删除「${record.name}}」？`,
      content: '一旦删除，在线服务相关数据将无法复原，请谨慎操作',
      onOk() {
        deleteModelServing_new(projectId!, record.id)
          .then(() => {
            Message.success('删除成功');
            listQuery.refetch();
          })
          .catch((error) => {
            Message.error(error.message);
          });
      },
    });
  }
  function onFilter(filter: Record<string, Array<number | string>>) {
    const filterParams: Record<string, any> = {};

    for (const key in filter) {
      filterParams[key] = booleanToString(filter[key]?.[0]);
    }

    setUrlState({
      is_local: filterParams.is_local,
      status: filterParams.status,
    });
  }
  function onSort(sorter: SorterResult) {
    const { field, direction: order } = sorter;
    if (field && order) {
      setUrlState({
        order_by: `${field as string} ${order === 'ascend' ? 'asc' : 'desc'}`,
      });
    } else {
      setUrlState({
        order_by: undefined,
      });
    }
  }
};

function booleanToString(val: any) {
  if (typeof val !== 'boolean') {
    return val;
  }
  return val ? 'true' : 'false';
}

export default ModelServingList;
