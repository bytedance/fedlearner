import React, { useMemo } from 'react';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantList } from 'hooks';
import {
  AlgorithmStatus,
  EnumAlgorithmProjectSource,
  EnumAlgorithmProjectType,
} from 'typings/algorithm';
import { ALGORITHM_TYPE_LABEL_MAPPER } from 'views/ModelCenter/shared';
import { Cascader, Divider, Space, Spin, Tag, Typography } from '@arco-design/web-react';

import styles from './index.module.less';
import { fetchPeerAlgorithmProjectList, fetchProjectList } from 'services/algorithm';
import { useQuery } from 'react-query';

const ALGORITHM_OWNER_TEXT_MAPPER = {
  self: '我方算法',
  peer: '合作伙伴算法',
  preset: '预置算法',
};

const ALGORITHM_OWNER_TAG_COLOR_MAPPER = {
  self: 'purple',
  peer: 'green',
  preset: 'blue',
};

interface Props {
  value?: ID;
  algorithmType?: EnumAlgorithmProjectType[];
  onChange?: (algorithmProjectUuid: ID) => void;
  supportEdit?: boolean;
}
export default function AlgorithmProjectSelect({
  algorithmType,
  value,
  onChange: onChangeFromProps,
  supportEdit = true,
}: Props) {
  const participantList = useGetCurrentProjectParticipantList();
  const projectId = useGetCurrentProjectId();

  const algorithmProjectListQuery = useQuery(
    ['fetchAllAlgorithmProjectList', algorithmType, projectId],
    () =>
      fetchProjectList(projectId, {
        type: algorithmType,
      }),
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const preAlgorithmProjectListQuery = useQuery(
    ['fetchPreAlgorithmProjectListQuery', algorithmType],
    () =>
      fetchProjectList(0, {
        type: algorithmType,
        sources: EnumAlgorithmProjectSource.PRESET,
      }),
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const peerAlgorithmProjectListQuery = useQuery(
    ['fetchPeerAlgorithmProjectListQuery', projectId, algorithmType],
    () =>
      fetchPeerAlgorithmProjectList(projectId, 0, {
        filter: `(type:${JSON.stringify(algorithmType)})`,
      }),
    {
      enabled: Boolean(projectId),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const algorithmProjectList = useMemo(() => {
    return [
      ...(algorithmProjectListQuery?.data?.data || []),
      ...(preAlgorithmProjectListQuery.data?.data || []),
    ].filter(
      (algorithmProject) =>
        algorithmProject.source === 'PRESET' ||
        algorithmProject.publish_status === AlgorithmStatus.PUBLISHED,
    );
  }, [algorithmProjectListQuery, preAlgorithmProjectListQuery]);
  const peerAlgorithmProjectList = useMemo(() => {
    return peerAlgorithmProjectListQuery.data?.data || [];
  }, [peerAlgorithmProjectListQuery]);

  const cascaderOptions = useMemo(() => {
    return [
      {
        value: 'self',
        label: '我方算法',
        disabled: algorithmProjectList?.length === 0,
        children: algorithmProjectList?.map((item) => ({
          ...item,
          value: item.uuid,
          label: item.name,
          participantName: item.source === EnumAlgorithmProjectSource.PRESET ? '预置' : '我方',
        })),
      },
      {
        value: 'peer',
        label: '合作伙伴算法',
        disabled: peerAlgorithmProjectList?.length === 0,
        children: peerAlgorithmProjectList?.map((item) => ({
          ...item,
          value: item.uuid,
          label: item.name,
          participantName: participantList.find(
            (participant) => participant.id === item.participant_id,
          )?.name,
        })),
      },
    ];
  }, [algorithmProjectList, peerAlgorithmProjectList, participantList]);

  const algorithmOwnerType = useMemo(() => {
    if (algorithmProjectList?.find((item) => item.uuid === value)) {
      return 'self';
    } else if (peerAlgorithmProjectList.find((item) => item.uuid === value)) {
      return 'peer';
    }
    return undefined;
  }, [value, algorithmProjectList, peerAlgorithmProjectList]);
  const algorithmProjectName = useMemo(() => {
    return [...algorithmProjectList, ...peerAlgorithmProjectList].find(
      (item) => item.uuid === value,
    )?.name;
  }, [value, algorithmProjectList, peerAlgorithmProjectList]);

  const algorithmTagType = useMemo(() => {
    const algorithmProject = algorithmProjectList?.find((item) => item.uuid === value);
    if (algorithmProject) {
      return algorithmProject.source === EnumAlgorithmProjectSource.PRESET ? 'preset' : 'self';
    } else if (peerAlgorithmProjectList.find((item) => item.uuid === value)) {
      return 'peer';
    }
    return undefined;
  }, [algorithmProjectList, peerAlgorithmProjectList, value]);

  const isLoading = useMemo(() => {
    return (
      algorithmProjectListQuery.isFetching ||
      peerAlgorithmProjectListQuery.isFetching ||
      preAlgorithmProjectListQuery.isFetching
    );
  }, [
    algorithmProjectListQuery.isFetching,
    peerAlgorithmProjectListQuery.isFetching,
    preAlgorithmProjectListQuery.isFetching,
  ]);

  return supportEdit ? (
    <Cascader
      loading={isLoading}
      options={cascaderOptions}
      placeholder="请选择算法"
      showSearch={true}
      onChange={(value) => {
        handleChange(value?.[1] as ID);
      }}
      renderOption={(option, level) => {
        if (level === 0) {
          return <span>{option.label}</span>;
        }
        return (
          <div className={styles.second_option_container}>
            <span style={{ display: 'block' }}>{option.name}</span>
            <Space className={styles.second_option_content} split={<Divider type="vertical" />}>
              <span>{option.participantName}</span>
              <span>{ALGORITHM_TYPE_LABEL_MAPPER?.[option.type as string]}</span>
            </Space>
          </div>
        );
      }}
    />
  ) : (
    <Spin loading={isLoading}>
      {!algorithmOwnerType || !algorithmProjectName || !algorithmTagType ? (
        <Typography.Text bold={true}> 暂无数据</Typography.Text>
      ) : (
        <Space>
          <Typography.Text bold={true}>{algorithmProjectName}</Typography.Text>
          <Tag color={ALGORITHM_OWNER_TAG_COLOR_MAPPER[algorithmTagType]}>
            {ALGORITHM_OWNER_TEXT_MAPPER[algorithmTagType]}
          </Tag>
        </Space>
      )}
    </Spin>
  );
  function handleChange(algorithmProjectUuid: ID) {
    onChangeFromProps?.(algorithmProjectUuid);
  }
}
