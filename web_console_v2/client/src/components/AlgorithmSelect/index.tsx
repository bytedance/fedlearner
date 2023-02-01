import React, { useMemo } from 'react';
import { Cascader, Select, Grid, Input, Space, Divider } from '@arco-design/web-react';
import {
  AlgorithmParameter,
  AlgorithmVersionStatus,
  EnumAlgorithmProjectSource,
  EnumAlgorithmProjectType,
} from 'typings/algorithm';
import { useQuery } from 'react-query';
import {
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
  useGetCurrentProjectParticipantName,
} from 'hooks';
import {
  fetchProjectList,
  fetchPeerAlgorithmProjectList,
  fetchPeerAlgorithmList,
  fetchAlgorithmList,
  fetchProjectDetail,
} from 'services/algorithm';

import styles from './index.module.less';

const { Row, Col } = Grid;

const ALGORITHM_TYPE_LABEL_MAPPER: Record<string, string> = {
  NN_HORIZONTAL: '横向联邦-NN模型',
  NN_VERTICAL: '纵向联邦-NN模型',
  TRUSTED_COMPUTING: '可信计算',
  UNSPECIFIED: '自定义模型',
};

interface Props {
  value?: AlgorithmSelectValue;
  leftDisabled?: boolean;
  rightDisabled?: boolean;
  isParticipant?: boolean;
  algorithmType?: EnumAlgorithmProjectType[];
  algorithmOwnerType: string;
  showHyperParameters?: boolean;
  filterReleasedAlgo?: boolean;
  onChange?: (value: AlgorithmSelectValue) => void;
  onAlgorithmOwnerChange?: (algorithmOwnerType: string) => void;
}
export type AlgorithmSelectValue = {
  algorithmProjectId?: ID;
  algorithmId?: ID;
  algorithmProjectUuid?: ID;
  algorithmUuid?: ID;
  config?: AlgorithmParameter[];
  path?: string;
  participantId?: ID;
};

function AlgorithmSelect({
  value,
  leftDisabled = false,
  rightDisabled = false,
  isParticipant = false,
  algorithmType = [],
  algorithmOwnerType,
  showHyperParameters = true,
  filterReleasedAlgo = false,
  onChange: onChangeFromProps,
  onAlgorithmOwnerChange,
}: Props) {
  const projectId = useGetCurrentProjectId();
  const participantName = useGetCurrentProjectParticipantName();
  const participantList = useGetCurrentProjectParticipantList();

  const leftValue = useMemo(() => {
    //支持选择合作伙伴后algorithmProjectId不唯一
    return [algorithmOwnerType, value?.algorithmProjectUuid as string];
  }, [value, algorithmOwnerType]);
  const algorithmProjectListQuery = useQuery(
    ['fetchAllAlgorithmProjectList', ...algorithmType, projectId, value?.algorithmProjectUuid],
    () =>
      fetchProjectList(projectId, {
        type: algorithmType,
      }),
    {
      enabled: Boolean(projectId),
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        const data = res.data;
        const algorithmProjectId = data.find((item) => item.uuid === value?.algorithmProjectUuid)
          ?.id;
        if (algorithmProjectId && value?.algorithmProjectId === undefined) {
          onChangeFromProps?.({ ...value, algorithmProjectId: algorithmProjectId });
        }
      },
    },
  );
  const preAlgorithmProjectListQuery = useQuery(
    ['fetchPreAlgorithmProjectListQuery', algorithmType, value?.algorithmProjectUuid],
    () =>
      fetchProjectList(0, {
        type: algorithmType,
        sources: EnumAlgorithmProjectSource.PRESET,
      }),
    {
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        const data = res.data;
        const algorithmProjectId = data.find((item) => item.uuid === value?.algorithmProjectUuid)
          ?.id;
        if (algorithmProjectId && value?.algorithmProjectId === undefined) {
          onChangeFromProps?.({ ...value, algorithmProjectId: algorithmProjectId });
        }
      },
    },
  );
  const peerAlgorithmProjectListQuery = useQuery(
    ['fetchPeerAlgorithmProjectListQuery', projectId, algorithmType],
    () =>
      fetchPeerAlgorithmProjectList(projectId, 0, {
        filter: `(type:${JSON.stringify(algorithmType)})`,
      }),
    {
      enabled: Boolean(projectId) || projectId === 0,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const algorithmProjectDetailQuery = useQuery(
    ['fetchAlgorithmProjectDetail', value],
    () => fetchProjectDetail(value?.algorithmProjectId!),
    {
      enabled:
        leftDisabled &&
        value?.algorithmProjectUuid === undefined &&
        value?.algorithmProjectId !== undefined,
      // 旧的工作区编辑时服务端不返回algorithmProjectUuid
      onSuccess(res) {
        const algorithmProjectDetail = res.data;
        onChangeFromProps?.({
          ...value,
          algorithmProjectUuid: algorithmProjectDetail?.uuid,
        });
      },
    },
  );

  const algorithmListQuery = useQuery(
    ['getAlgorithmListDetail', value?.algorithmProjectId],
    () => fetchAlgorithmList(0, { algo_project_id: value?.algorithmProjectId! }),
    {
      enabled:
        !isParticipant &&
        leftValue?.[0] === 'self' &&
        (Boolean(value?.algorithmProjectId) || value?.algorithmProjectId === 0),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const peerAlgorithmListQuery = useQuery(
    ['getPeerAlgorithmList', projectId, value?.participantId, value?.algorithmProjectUuid],
    () =>
      fetchPeerAlgorithmList(projectId, value?.participantId, {
        algorithm_project_uuid: value?.algorithmProjectUuid!,
      }),
    {
      enabled:
        !isParticipant &&
        leftValue?.[0] === 'peer' &&
        Boolean(value?.algorithmProjectUuid) &&
        Boolean(value?.participantId),
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const algorithmProjectList = useMemo(() => {
    return [
      ...(algorithmProjectListQuery?.data?.data || []),
      ...(preAlgorithmProjectListQuery.data?.data || []),
    ];
  }, [algorithmProjectListQuery, preAlgorithmProjectListQuery]);
  const peerAlgorithmProjectList = useMemo(() => {
    return peerAlgorithmProjectListQuery.data?.data || [];
  }, [peerAlgorithmProjectListQuery]);

  const configValueList = useMemo(() => {
    return value?.config || [];
  }, [value?.config]);

  const algorithmProjectDetail = useMemo(() => {
    return leftValue?.[0] === 'self'
      ? algorithmListQuery.data?.data
      : peerAlgorithmListQuery.data?.data;
  }, [leftValue, algorithmListQuery, peerAlgorithmListQuery]);

  const rightValue = useMemo(() => {
    if (value?.algorithmId !== null && value?.algorithmId !== 0 && algorithmOwnerType === 'self') {
      return algorithmProjectDetail?.find((item) => item.id === value?.algorithmId)?.uuid;
    }
    return value?.algorithmUuid;
  }, [value, algorithmProjectDetail, algorithmOwnerType]);

  const leftOptions = useMemo(() => {
    return [
      {
        value: 'self',
        label: '我方算法',
        disabled: algorithmProjectList.length === 0,
        children: algorithmProjectList.map((item) => ({
          ...item,
          value: item.uuid,
          label: item.name,
          participantName: '我方',
        })),
      },
      {
        value: 'peer',
        label: '合作伙伴算法',
        disabled: peerAlgorithmProjectList.length === 0,
        children: peerAlgorithmProjectList.map((item) => ({
          ...item,
          value: item.uuid,
          label: item.name,
          participantName:
            participantList.find((participant) => participant.id === item.participant_id)?.name ||
            participantName,
        })),
      },
    ];
  }, [algorithmProjectList, peerAlgorithmProjectList, participantName, participantList]);

  const rightOptions = useMemo(() => {
    if (filterReleasedAlgo) {
      const releasedAlgo = algorithmProjectDetail?.filter(
        (item) => item.status === AlgorithmVersionStatus.PUBLISHED,
      );
      return (
        releasedAlgo?.map((item) => ({
          label: `V${item.version}`,
          value: item.uuid as ID,
          extra: item,
        })) || []
      );
    }

    return (
      algorithmProjectDetail?.map((item) => ({
        label: `V${item.version}`,
        value: item.uuid as ID,
        extra: item,
      })) || []
    );
  }, [algorithmProjectDetail, filterReleasedAlgo]);

  return (
    <>
      {!isParticipant && (
        <Row gutter={12}>
          <Col span={16}>
            <Cascader
              className={styles.cascader_container}
              value={leftValue?.[1] ? leftValue : undefined}
              options={leftOptions}
              placeholder="请选择算法"
              showSearch={true}
              onChange={(value, selectedOptions) => {
                onAlgorithmOwnerChange?.(value?.[0] as string);
                onChange({ algorithmProjectUuid: value?.[1] as ID, algorithmUuid: undefined });
              }}
              disabled={leftDisabled}
              renderOption={(option, level) => {
                if (level === 0) {
                  return <span>{option.label}</span>;
                }
                return (
                  <div className={styles.second_option_container}>
                    <span style={{ display: 'block' }}>{option.name}</span>
                    <Space
                      className={styles.second_option_content}
                      split={<Divider type="vertical" />}
                    >
                      <span>{option.participantName}</span>
                      <span>{ALGORITHM_TYPE_LABEL_MAPPER?.[option.type as string]}</span>
                    </Space>
                  </div>
                );
              }}
            />
          </Col>
          <Col span={8}>
            <Select
              options={rightOptions}
              value={rightValue}
              disabled={rightDisabled}
              onChange={(value) => {
                onChange({ algorithmProjectUuid: leftValue?.[1] as ID, algorithmUuid: value });
              }}
            />
          </Col>
        </Row>
      )}
      {showHyperParameters && configValueList.length > 0 && (
        <>
          {!isParticipant && (
            <Row gutter={[12, 12]}>
              <Col span={12}>超参数</Col>
            </Row>
          )}
          <Row gutter={[12, 12]}>
            {configValueList.map((item, index) => (
              <React.Fragment key={`${rightValue}_${item.name}_${index}`}>
                <Col span={12}>
                  <Input
                    value={item.name}
                    onChange={(value) => onConfigValueChange(value, 'name', index)}
                    disabled={true}
                  />
                </Col>
                <Col span={12}>
                  <Input
                    value={item.value}
                    onChange={(value) => onConfigValueChange(value, 'value', index)}
                  />
                </Col>
              </React.Fragment>
            ))}
          </Row>
        </>
      )}
      {showHyperParameters && isParticipant && configValueList.length <= 0 && (
        <span className={styles.text_content}>对侧无算法超参数，无需配置</span>
      )}
    </>
  );

  function onConfigValueChange(val: string, key: string, index: number) {
    const newConfigValueList = [...configValueList];
    newConfigValueList[index] = { ...newConfigValueList[index], [key]: val };
    onChangeFromProps?.({
      ...value,
      config: newConfigValueList,
    });
  }

  function onChange(val: { algorithmProjectUuid?: ID; algorithmUuid?: ID }) {
    const rightItem = rightOptions.find((item) => item.value === val.algorithmUuid);

    const config = rightItem?.extra?.parameter?.variables ?? [];
    const path = rightItem?.extra?.path ?? '';
    const algorithmId = rightItem?.extra?.id;
    const algorithmProjectId = [...algorithmProjectList, ...peerAlgorithmProjectList].find(
      (item) => item.uuid === val.algorithmProjectUuid,
    )?.id;
    const participantId =
      peerAlgorithmProjectList.find((item) => item.uuid === val.algorithmProjectUuid)
        ?.participant_id ?? 0;

    onChangeFromProps?.({
      ...val,
      config,
      path,
      algorithmId,
      algorithmProjectId,
      participantId,
    });
  }
}
export default AlgorithmSelect;
