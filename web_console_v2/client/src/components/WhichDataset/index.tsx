/* istanbul ignore file */
import React, { FC } from 'react';

import { formatIntersectionDatasetName } from 'shared/modelCenter';

import { useRecoilQuery } from 'hooks/recoil';
import { intersectionDatasetListQuery } from 'stores/dataset';
import { CONSTANTS } from 'shared/constants';

import { Spin } from '@arco-design/web-react';
import { Dataset, IntersectionDataset } from 'typings/dataset';
import { useQuery } from 'react-query';
import { fetchDatasetDetail, fetchDatasetList } from 'services/dataset';
import { FILTER_OPERATOR_MAPPER, filterExpressionGenerator } from 'views/Datasets/shared';

type Props = {
  id?: ID;
  loading?: boolean;
};

const WhichDataset: FC<Props> & {
  UUID: FC<UUIDProps>;
  IntersectionDataset: FC<Props>;
  DatasetDetail: FC<Props>;
} = ({ id, loading }) => {
  const datasetListQuery = useQuery(
    ['fetchDatasetList', 'WhichDataset', id],
    () => {
      return fetchDatasetList().then((res) => {
        return (res?.data || []).filter((item) => String(item.id) === String(id));
      });
    },
    {
      enabled: Boolean(id),
      refetchOnWindowFocus: false,
      retry: 2,
    },
  );

  if (loading || datasetListQuery.isFetching) {
    return <Spin />;
  }

  return <span>{datasetListQuery.data?.[0]?.name ?? CONSTANTS.EMPTY_PLACEHOLDER}</span>;
};

// TODO: add mode props,for search raw dataset or intersection dataset
const _IntersectionDataset: FC<Props> = ({ id, loading }) => {
  const { isLoading, data } = useRecoilQuery(intersectionDatasetListQuery);

  if (loading || isLoading) {
    return <Spin />;
  }

  const item =
    data?.find((innerItem: any) => Number(innerItem.id) === Number(id)) ||
    ({
      name: CONSTANTS.EMPTY_PLACEHOLDER,
    } as IntersectionDataset);

  return <span>{formatIntersectionDatasetName(item)}</span>;
};

type UUIDProps = {
  uuid: string;
  loading?: boolean;
  onAPISuccess?: (data?: Dataset) => void;
  displayKey?: Partial<keyof Dataset>;
};

const _UUID: FC<UUIDProps> = ({ uuid, loading, onAPISuccess, displayKey = 'name' }) => {
  const datasetListQuery = useQuery(
    ['fetchDatasetList', uuid],
    () =>
      fetchDatasetList({
        filter: filterExpressionGenerator(
          {
            uuid,
          },
          FILTER_OPERATOR_MAPPER,
        ),
      }),
    {
      enabled: Boolean(uuid),
      refetchOnWindowFocus: false,
      retry: 2,
      onSuccess(res) {
        onAPISuccess?.(res.data?.[0] ?? undefined);
      },
    },
  );

  if (loading || datasetListQuery.isFetching) {
    return <Spin />;
  }

  return <span>{datasetListQuery.data?.data?.[0]?.[displayKey] ?? '数据集已删除'}</span>;
};

const _DatasetDetail: FC<Props> = ({ id, loading }) => {
  const datasetDetailQuery = useQuery(
    ['fetchDatasetDetail', 'WhichDataset', id],
    () => {
      return fetchDatasetDetail(id).then((res) => {
        return res.data;
      });
    },
    {
      enabled: Boolean(id),
      refetchOnWindowFocus: false,
      retry: 2,
    },
  );

  if (loading || datasetDetailQuery.isFetching) {
    return <Spin />;
  }

  return <div>{datasetDetailQuery.data?.name ?? CONSTANTS.EMPTY_PLACEHOLDER}</div>;
};

WhichDataset.UUID = _UUID;
WhichDataset.IntersectionDataset = _IntersectionDataset;
WhichDataset.DatasetDetail = _DatasetDetail;

export default WhichDataset;
