import React, { FC, useMemo, useState } from 'react';
import { useHistory } from 'react-router';
import { useQuery } from 'react-query';

import request from 'libs/request';
import {
  fetchProjectDetail,
  fetchProjectList,
  postPublishAlgorithm,
  getFullAlgorithmProjectDownloadHref,
  publishAlgorithm,
} from 'services/algorithm';
import { forceToRefreshQuery } from 'shared/queryClient';
import { TIME_INTERVAL } from 'shared/constants';

import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useTablePaginationWithUrlState,
  useUrlState,
} from 'hooks';

import { Button, Input, Message } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import GridRow from 'components/_base/GridRow';
import AlgorithmTable from '../AlgorithmTable';
import showSendModal from '../../AlgorithmSendModal';
import { AlgorithmProject, EnumAlgorithmProjectSource } from 'typings/algorithm';
import {
  deleteConfirm,
  FILTER_ALGORITHM_MY_OPERATOR_MAPPER,
} from 'views/AlgorithmManagement/shared';
import { filterExpressionGenerator } from 'views/Datasets/shared';
import { expression2Filter } from 'shared/filter';

export const LIST_QUERY_KEY = 'my_algorithm_list_query';

const MyAlgorithmTab: FC = () => {
  const history = useHistory();
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
  const listQueryKey = [LIST_QUERY_KEY, projectId, urlState];
  const listQuery = useQuery(
    listQueryKey,
    () => {
      if (!projectId) {
        Message.info('请选择工作区');
      }
      return fetchProjectList(projectId ?? 0, {
        ...urlState,
        sources: [EnumAlgorithmProjectSource.USER, EnumAlgorithmProjectSource.THIRD_PARTY],
      });
    },
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
        <Button
          className="custom-operation-button"
          type="primary"
          icon={<IconPlus />}
          onClick={onCreateClick}
        >
          创建算法
        </Button>

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
        data={listQuery.data?.data ?? []}
        urlState={urlState}
        setUrlState={setUrlState}
        noDataElement="暂无算法，去创建"
        loading={listQuery.isFetching}
        participant={participantList ?? []}
        pagination={pagination}
        onReleaseClick={onReleaseClick}
        onPublishClick={onPublishClick}
        onChangeClick={onChangeClick}
        onDeleteClick={onDeleteClick}
        onDownloadClick={onDownloadClick}
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

  function onCreateClick() {
    history.push('/algorithm-management/create');
  }
  function onChangeClick(record: any) {
    history.push(`/algorithm-management/edit?id=${record.id}`);
  }

  function onReleaseClick(record: any) {
    showSendModal(
      record,
      async (comment: string) => {
        await postPublishAlgorithm(record.id, comment);
        forceToRefreshQuery([...listQueryKey]);
        Message.success('发版成功');
      },
      () => {},
      true,
    );
  }

  function onPublishClick(record: AlgorithmProject) {
    // indicate that there're not any algorithm
    if (record.latest_version === 0) {
      return;
    }
    showSendModal(
      () =>
        fetchProjectDetail(record.id).then((res) => {
          const latestAlgorithm = res.data?.algorithms?.[0];
          if (!latestAlgorithm) {
            Message.error('没有算法');
            throw new Error('no algorithm');
          }
          return latestAlgorithm;
        }),
      async (comment: string, algorithm) => {
        await publishAlgorithm(projectId, algorithm.id, { comment });
        Message.success('发布成功');
      },
      () => {},
      false,
    );
  }

  async function onDeleteClick(record: AlgorithmProject) {
    try {
      await deleteConfirm(record, true);
      forceToRefreshQuery([...listQueryKey]);
    } catch (e) {
      Message.error(e.message);
    }
  }
  async function onDownloadClick(record: AlgorithmProject) {
    try {
      const tip = await request.download(getFullAlgorithmProjectDownloadHref(record.id));
      tip && Message.info(tip);
    } catch (error) {
      Message.error(error.message);
    }
  }
};

export default MyAlgorithmTab;
