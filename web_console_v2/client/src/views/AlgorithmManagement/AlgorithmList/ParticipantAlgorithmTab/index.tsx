import React, { FC, useMemo, useState } from 'react';
import { useQuery } from 'react-query';

import { fetchPeerAlgorithmProjectList } from 'services/algorithm';
import { TIME_INTERVAL } from 'shared/constants';
import { expression2Filter } from 'shared/filter';
import { pageSplit } from '../../shared';
import AlgorithmTable from '../AlgorithmTable';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useTablePaginationWithUrlState,
  useUrlState,
} from 'hooks';
import GridRow from 'components/_base/GridRow';
import { Input } from '@arco-design/web-react';
import { FILTER_ALGORITHM_MY_OPERATOR_MAPPER } from 'views/AlgorithmManagement/shared';
import { filterExpressionGenerator } from 'views/Datasets/shared';

export const LIST_QUERY_KEY = 'PresetAlgorithmProjects';

const ParticipantAlgorithmTab: FC = () => {
  const projectId = useGetCurrentProjectId();
  const participantList = useGetCurrentProjectParticipantList();
  const [total, setTotal] = useState(0);
  const [pageTotal, setPageTotal] = useState(0);
  const { paginationProps } = useTablePaginationWithUrlState();
  const [urlState, setUrlState] = useUrlState({
    page: 1,
    pageSize: 10,
    filter: filterExpressionGenerator(
      {
        project_id: projectId,
      },
      FILTER_ALGORITHM_MY_OPERATOR_MAPPER,
    ),
    order_by: '',
  });

  const listQuery = useQuery(
    [LIST_QUERY_KEY, projectId, urlState],
    () =>
      fetchPeerAlgorithmProjectList(projectId, 0, {
        filter: urlState.filter,
      }),
    {
      retry: 2,
      refetchInterval: TIME_INTERVAL.LIST, // auto refresh every 1.5 min
      onSuccess: (res) => {
        setTotal((pre) => res.data?.length || pre);
        setPageTotal(Math.ceil(res.data?.length / urlState.pageSize) ?? 0);
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

  const list = useMemo(() => {
    if (!listQuery.data?.data) return [];
    const { page, pageSize } = urlState;
    return pageSplit(listQuery.data.data, page, pageSize);
  }, [listQuery.data, urlState]);

  return (
    <>
      <GridRow justify="end" align="center">
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
        data={list}
        urlState={urlState}
        setUrlState={setUrlState}
        noDataElement="暂无算法，去创建"
        isParticipant={true}
        participant={participantList ?? []}
        pagination={pagination}
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
};

export default ParticipantAlgorithmTab;
