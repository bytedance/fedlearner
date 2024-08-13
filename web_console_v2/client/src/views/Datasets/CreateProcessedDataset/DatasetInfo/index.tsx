/* istanbul ignore file */

import React, { FC, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { Tag } from '@arco-design/web-react';
import { DATASET_LIST_QUERY_KEY } from 'views/Datasets/DatasetList';
import { fetchDatasetList, fetchParticipantDatasetList } from 'services/dataset';
import { Dataset, ParticipantDataset, DatasetKindBackEndType } from 'typings/dataset';
import { useRecoilValue } from 'recoil';
import { projectState } from 'stores/project';
import { PageMeta } from 'typings/app';
import { FILTER_OPERATOR_MAPPER, filterExpressionGenerator } from 'views/Datasets/shared';
import styled from './index.module.less';

interface Props {
  datasetUuid: string;
  participantId?: ID;
  isParticipant?: boolean;
}

const DatasetInfo: FC<Props> = ({ isParticipant = false, datasetUuid, participantId }) => {
  const selectedProject = useRecoilValue(projectState);
  const [currentDataset, setCurrentDataset] = useState<Dataset | ParticipantDataset>();
  const query = useQuery<{
    data: Array<Dataset | ParticipantDataset>;
    page_meta?: PageMeta;
  }>(
    [
      DATASET_LIST_QUERY_KEY,
      selectedProject.current?.id,
      datasetUuid,
      participantId,
      isParticipant,
    ],
    () => {
      const filter = filterExpressionGenerator(
        {
          project_id: selectedProject.current?.id,
          is_published: isParticipant ? undefined : true,
          uuid: datasetUuid,
        },
        FILTER_OPERATOR_MAPPER,
      );
      if (isParticipant) {
        return fetchParticipantDatasetList(selectedProject.current?.id!, {
          uuid: datasetUuid,
          participant_id: participantId,
        });
      }
      return fetchDatasetList({
        filter,
      });
    },
    {
      enabled: Boolean(selectedProject.current),
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess: (res) => {
        setCurrentDataset(res.data[0]);
      },
    },
  );
  // Empty only if there is no keyword, and the 1st page is requested, and there is no data
  const isEmpty = !query.isFetching && !currentDataset;
  const tagText = useMemo(() => {
    let tagText = '';
    if (!currentDataset) return tagText;
    if (currentDataset.dataset_kind === DatasetKindBackEndType.RAW) {
      tagText = '原始';
    }
    if (currentDataset.dataset_kind === DatasetKindBackEndType.PROCESSED) {
      tagText = '结果';
    }
    return tagText;
  }, [currentDataset]);
  return (
    <>
      {isEmpty ? (
        <div>暂无数据集</div>
      ) : (
        <div className={styled.dataset_processed_desc}>
          <span className={styled.dataset_processed_name}>{currentDataset?.name}</span>
          {tagText ? <Tag>{tagText}</Tag> : <></>}
        </div>
      )}
    </>
  );
};

export default DatasetInfo;
