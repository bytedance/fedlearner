import { PageMeta } from 'typings/app';
import { useRecoilValue } from 'recoil';
import { useMemo, useState } from 'react';
import { IPageInfo, Props } from './index';
import { projectState } from 'stores/project';
import { Message } from '@arco-design/web-react';
import { useQuery, UseQueryResult } from 'react-query';
import { DATASET_LIST_QUERY_KEY } from 'views/Datasets/DatasetList';
import {
  Dataset,
  DatasetKindLabelCapitalMapper,
  DatasetStateFront,
  ParticipantDataset,
} from 'typings/dataset';
import {
  fetchDatasetDetail,
  fetchDatasetList,
  fetchParticipantDatasetList,
} from 'services/dataset';
import { FILTER_OPERATOR_MAPPER, filterExpressionGenerator } from 'views/Datasets/shared';

type TGetDatasetList = [
  Array<Dataset | ParticipantDataset>,
  UseQueryResult<
    {
      data: Array<Dataset | ParticipantDataset>;
    },
    unknown
  >,
  IPageInfo,
  (args: any) => void,
  () => void,
  (args: Array<Dataset | ParticipantDataset>) => void,
];

/**
 * fetch dataset list depends lazy or not
 * @param isParticipant
 * @param queryParams
 * @param kind
 * @param lazyLoad
 * @param disabled
 * @param datasetJobKind
 */
export function useGetDatasetList({
  isParticipant,
  queryParams,
  kind,
  lazyLoad = {
    enable: false,
    page_size: 10,
  },
  disabled,
  datasetJobKind,
}: Pick<
  Props,
  'isParticipant' | 'queryParams' | 'kind' | 'lazyLoad' | 'disabled' | 'datasetJobKind'
>): TGetDatasetList {
  const selectedProject = useRecoilValue(projectState);
  const [pageInfo, setPageInfo] = useState<IPageInfo>({
    page: 1,
    totalPages: 0,
    keyword: '',
  });
  const [options, setOptions] = useState([] as Array<ParticipantDataset | Dataset>);

  const query = useQuery<{
    data: Array<Dataset | ParticipantDataset>;
    page_meta?: PageMeta;
  }>(
    [
      DATASET_LIST_QUERY_KEY,
      selectedProject.current?.id,
      isParticipant,
      kind,
      lazyLoad?.enable ? pageInfo.page : null,
      lazyLoad?.enable ? pageInfo.keyword : null,
      disabled,
      datasetJobKind,
    ],
    () => {
      const pageParams = lazyLoad?.enable
        ? {
            page: pageInfo.page,
            page_size: lazyLoad.page_size,
          }
        : {};
      const filter = filterExpressionGenerator(
        {
          project_id: selectedProject.current?.id,
          name: pageInfo.keyword,
          is_published: isParticipant ? undefined : true,
          dataset_kind: isParticipant ? undefined : DatasetKindLabelCapitalMapper[kind!],
        },
        FILTER_OPERATOR_MAPPER,
      );
      if (isParticipant) {
        return fetchParticipantDatasetList(selectedProject.current?.id!, {
          ...queryParams,
          ...pageParams,
        });
      }
      return fetchDatasetList({
        filter,
        ...queryParams,
        ...pageParams,
        state_frontend: [DatasetStateFront.SUCCEEDED],
        dataset_job_kind: datasetJobKind,
      });
    },
    {
      enabled: Boolean(selectedProject.current && !disabled),
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess: (res) => {
        setPageInfo((pre) => {
          const { page_meta } = res;
          return {
            ...pre,
            page: page_meta?.current_page || pre.page,
            totalPages: page_meta?.total_pages || pre.totalPages,
          };
        });
        setOptions((pre) => {
          const { data } = res;
          const addOption = (data ?? []) as Dataset[];
          return pre.concat(addOption);
        });
      },
    },
  );

  const list = useMemo(() => {
    return options;
  }, [options]);

  const clearList = () => {
    setOptions([]);
  };

  return [list, query, pageInfo, setPageInfo, clearList, setOptions] as TGetDatasetList;
}

/**
 * Gets the details of the last selected dataset when the page is initialized
 * @param datasetId
 * @param pageInit
 */
export function useGetLastSelectedDataset(datasetId: ID, pageInit: boolean) {
  const detailDataQuery = useQuery(
    ['fetch_last_dataset_detail', datasetId, pageInit],
    () => fetchDatasetDetail(datasetId),
    {
      enabled: Boolean(pageInit && (datasetId || datasetId === 0)),
      retry: false,
      refetchOnWindowFocus: false,
      onError: (error: any) => {
        Message.error(error.message);
      },
    },
  );

  const isLoading = useMemo(() => {
    return detailDataQuery.isFetching;
  }, [detailDataQuery]);

  const data = useMemo(() => {
    if (!detailDataQuery?.data) {
      return undefined;
    }
    return detailDataQuery?.data?.data;
  }, [detailDataQuery]);

  return [isLoading, data] as [boolean, undefined | Dataset | ParticipantDataset];
}
