import React, { FC, useMemo, useState } from 'react';
import { useMutation, useQuery } from 'react-query';

import { EnumAlgorithmProjectSource } from 'typings/algorithm';
import { fetchProjectList, updatePresetAlgorithm } from 'services/algorithm';
import { TIME_INTERVAL } from 'shared/constants';
import AlgorithmTable from '../AlgorithmTable';
import {
  useGetCurrentProjectParticipantList,
  useTablePaginationWithUrlState,
  useUrlState,
} from 'hooks';
import GridRow from 'components/_base/GridRow';
import { Button, Input, Message, Tooltip } from '@arco-design/web-react';
import { useIsAdminRole } from 'hooks/user';
import { expression2Filter } from 'shared/filter';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { FILTER_ALGORITHM_MY_OPERATOR_MAPPER } from 'views/AlgorithmManagement/shared';

export const LIST_QUERY_KEY = 'PresetAlgorithmProjects';

const BuiltInAlgorithmTab: FC = () => {
  const participantList = useGetCurrentProjectParticipantList();
  const isAdminRole = useIsAdminRole();

  const [total, setTotal] = useState(0);
  const [pageTotal, setPageTotal] = useState(0);
  const { paginationProps } = useTablePaginationWithUrlState();
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: '',
    order_by: '',
  });

  const listQuery = useQuery(
    [LIST_QUERY_KEY, urlState],
    () =>
      fetchProjectList(0, {
        ...urlState,
        sources: EnumAlgorithmProjectSource.PRESET,
      }),
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
      onSuccess: (res) => {
        const { page_meta } = res || {};
        setTotal((pre) => page_meta?.total_items || pre);
        setPageTotal(page_meta?.total_pages ?? 0);
      },
    },
  );

  const updatePresetAlgorithmMutation = useMutation(
    (payload: any) => {
      return updatePresetAlgorithm(payload);
    },
    {
      onSuccess() {
        Message.success('更新预置算法成功');
        listQuery.refetch();
      },
      onError(e: any) {
        Message.error(e.message);
      },
    },
  );

  const pagination = useMemo(() => {
    return pageTotal <= 1
      ? false
      : {
          ...paginationProps,
          total,
        };
  }, [paginationProps, pageTotal, total]);

  return (
    <>
      <GridRow justify="space-between" align="center">
        <Tooltip content="只有管理员才能更新预置算法" disabled={isAdminRole}>
          <Button
            className="custom-operation-button"
            type="primary"
            onClick={onUpdateClick}
            loading={updatePresetAlgorithmMutation.isLoading}
            disabled={!isAdminRole}
          >
            更新预置算法
          </Button>
        </Tooltip>

        <Input.Search
          className="custom-input"
          allowClear
          defaultValue={expression2Filter(urlState.filter).name}
          onSearch={onSearch}
          onClear={() => onSearch('')}
          placeholder="输入算法名称"
        />
      </GridRow>
      <AlgorithmTable
        loading={listQuery.isFetching}
        data={listQuery.data?.data ?? []}
        urlState={urlState}
        setUrlState={setUrlState}
        isBuiltIn={true}
        pagination={pagination}
        noDataElement="暂无算法"
        participant={participantList ?? []}
      />
    </>
  );

  function onSearch(value: string) {
    const filters = expression2Filter(urlState.filter);
    filters.name = value;
    setUrlState((prevState) => ({
      ...prevState,
      page: 1,
      filter: filterExpressionGenerator(filters, FILTER_ALGORITHM_MY_OPERATOR_MAPPER),
    }));
  }
  function onUpdateClick() {
    updatePresetAlgorithmMutation.mutate({});
  }
};

export default BuiltInAlgorithmTab;
