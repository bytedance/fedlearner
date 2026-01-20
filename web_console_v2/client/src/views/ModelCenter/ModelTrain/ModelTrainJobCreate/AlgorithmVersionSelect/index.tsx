import React, { useMemo } from 'react';
import { Select, Grid, Input } from '@arco-design/web-react';
import { AlgorithmParameter, AlgorithmProject, AlgorithmVersionStatus } from 'typings/algorithm';
import { useQuery } from 'react-query';
import { fetchAlgorithmList, fetchPeerAlgorithmList } from 'services/algorithm';
import { useGetCurrentProjectId } from 'hooks';

const { Row, Col } = Grid;
type AlgorithmVersionValue = {
  algorithmUuid?: ID;
  config?: AlgorithmParameter[];
};
interface Props {
  algorithmProjectList: AlgorithmProject[];
  peerAlgorithmProjectList: AlgorithmProject[];
  algorithmProjectUuid: ID;
  onChange?: (value: AlgorithmVersionValue) => void;
  value?: AlgorithmVersionValue;
}

export default function AlgorithmVersionSelect({
  algorithmProjectList,
  peerAlgorithmProjectList,
  algorithmProjectUuid,
  onChange: onSelectedAlgorithmVersionChange,
  value,
}: Props) {
  const projectId = useGetCurrentProjectId();
  const { algorithmOwner, selectedAlgorithmProject } = useMemo(() => {
    if (algorithmProjectList?.find((item) => item.uuid === algorithmProjectUuid)) {
      return {
        algorithmOwner: 'self',
        selectedAlgorithmProject: algorithmProjectList?.find(
          (item) => item.uuid === algorithmProjectUuid,
        ),
      };
    }
    if (peerAlgorithmProjectList?.find((item) => item.uuid === algorithmProjectUuid)) {
      return {
        algorithmOwner: 'peer',
        selectedAlgorithmProject: peerAlgorithmProjectList?.find(
          (item) => item.uuid === algorithmProjectUuid,
        ),
      };
    }
    return {};
  }, [algorithmProjectList, algorithmProjectUuid, peerAlgorithmProjectList]);

  const configValueList = useMemo(() => {
    return value?.config || [];
  }, [value?.config]);

  const algorithmVersionListQuery = useQuery(
    ['fetchAlgorithmVersionList', selectedAlgorithmProject, algorithmOwner],
    () => {
      if (algorithmOwner === 'self') {
        return fetchAlgorithmList(0, { algo_project_id: selectedAlgorithmProject?.id! });
      } else {
        return fetchPeerAlgorithmList(projectId, selectedAlgorithmProject?.participant_id!, {
          algorithm_project_uuid: selectedAlgorithmProject?.uuid!,
        });
      }
    },
    {
      enabled: Boolean(projectId && selectedAlgorithmProject && algorithmOwner),
    },
  );

  const algorithmVersionListOptions = useMemo(() => {
    return algorithmVersionListQuery.data?.data
      .filter(
        (item) => item.status === AlgorithmVersionStatus.PUBLISHED || item.source === 'PRESET',
      )
      .map((item) => {
        return {
          label: `V${item.version}`,
          value: item.uuid as string,
          extra: item,
        };
      });
  }, [algorithmVersionListQuery.data?.data]);

  return (
    <>
      <Select
        value={value?.algorithmUuid || undefined}
        options={algorithmVersionListOptions}
        onChange={handleSelectChange}
      />
      {configValueList.length > 0 && (
        <>
          <Row gutter={[12, 12]}>
            <Col span={12}>超参数</Col>
          </Row>

          {configValueList.map((item, index) => (
            <Row key={`${value?.algorithmUuid}_$${item.name}_${index}`} gutter={[12, 12]}>
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
            </Row>
          ))}
        </>
      )}
    </>
  );
  function handleSelectChange(val: any) {
    const selectedAlgorithm = algorithmVersionListOptions?.find((item) => item.value === val);
    onSelectedAlgorithmVersionChange?.({
      algorithmUuid: val,
      config: selectedAlgorithm?.extra.parameter?.variables || [],
    });
  }
  function onConfigValueChange(val: string, key: string, index: number) {
    const newConfigValueList = [...configValueList];
    newConfigValueList[index] = { ...newConfigValueList[index], [key]: val };
    onSelectedAlgorithmVersionChange?.({
      ...value,
      config: newConfigValueList,
    });
  }
}
