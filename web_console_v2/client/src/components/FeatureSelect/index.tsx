/* istanbul ignore file */

import { Button, Input, Select, Tooltip, Message, Alert } from '@arco-design/web-react';
import ErrorBoundary from 'components/ErrorBoundary';
import StructDataPreviewTable from 'components/DataPreview/StructDataTable';
import { Delete } from 'components/IconPark';
import NoResult from 'components/NoResult';
import GridRow from 'components/_base/GridRow';
import React, { FC } from 'react';
import { useQuery } from 'react-query';
import { useRecoilState } from 'recoil';
import { fetchDatasetPreviewData } from 'services/dataset';
import { datasetState } from 'stores/dataset';
import styled from 'styled-components';
import { MixinCommonTransition } from 'styles/mixins';

const Container = styled.div`
  position: relative;
  left: 250px;
  width: calc(100vw - 2 * var(--contentOuterPadding));
  min-height: 400px;
  display: flex;
  transform: translateX(-50%);
  border-top: 1px solid var(--lineColor);
`;
const NoResultContainer = styled.div`
  flex-shrink: 0;
  width: 100%;
  margin: 20px 0;
`;
const TableConatienr = styled.div`
  width: 50%;
  padding: 24px;
  padding-right: 0;
  padding-bottom: 0;
  border-right: 1px solid var(--lineColor);
  overflow: hidden;
`;
const SelectedConatienr = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  width: 50%;
  padding: 24px;

  > div + div {
    margin-left: 20px;
  }
`;
const Heading = styled.h4`
  margin-bottom: 20px;
  line-height: 20px;
  font-size: 13px;
  font-weight: 500;
`;
const SelectedFeatCol = styled.div`
  flex: 1;
  min-width: 150px;
  max-width: 250px;
`;
const MissingCountCol = styled.div`
  flex: 2;
  max-width: 400px;
`;
const FeatureDisplay = styled.div`
  ${MixinCommonTransition()}
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 20px;
  margin-bottom: 20px;
  padding-right: 10px;
  line-height: 22px;
  border-radius: 2px;
  background-color: var(--backgroundColor);
  cursor: pointer;

  &:hover {
    color: var(--primaryColor);
    background-color: white;
    box-shadow: 0 0 0 1px var(--primaryColor) inset;
  }
`;
const FeatureInput = styled(Input)`
  margin-bottom: 20px;
`;
const ButtonGroup = styled(GridRow)`
  width: 100%;
  flex: 0 0 auto;
`;
const InvalidAlert = styled(Alert)`
  width: 100%;
  margin-bottom: 10px;
`;

const CUSTOM_VALUE_TYPE = '_';
const VALUE_TYPE_OPTIONS = [
  {
    value: CUSTOM_VALUE_TYPE,
    label: '指定值',
    disabled: false,
  },
  {
    value: 'max',
    label: '最大值',
    disabled: true,
  },
  {
    value: 'min',
    label: '最小值',
    disabled: true,
  },
  {
    value: 'mean',
    label: '中位数',
    disabled: true,
  },
  {
    value: 'avg',
    label: '平均值',
    disabled: true,
  },
] as const;

type Props = {
  value?: string;
  onChange?: (val: string) => void;
};
type ParsedFeatures = { key: string; value: string }[];

let inputTimer: TimeoutID = undefined;

const FeatureSelect: FC<Props> = ({ value, onChange }) => {
  const checkedFeats = _parseValue(value);

  const [dataset] = useRecoilState(datasetState);
  const datasetId = dataset.current?.id;

  const previewDataQuery = useQuery(
    ['fetchStructPreviewData', datasetId],
    () => fetchDatasetPreviewData(datasetId!),
    {
      refetchOnWindowFocus: false,
      retry: 0,
      enabled: Boolean(datasetId),
    },
  );

  if (!datasetId) {
    return (
      <Container style={{ flexDirection: 'column' }}>
        <NoResult text="数据集ID不存在，请检查" />
        <GridRow justify="center">
          <Button onClick={onPreviousClick}>上一步</Button>
        </GridRow>
      </Container>
    );
  }

  const checkedKeys = checkedFeats.map((item) => item.key);
  const nothingChecked = checkedKeys.length === 0;

  return (
    <ErrorBoundary>
      <Container>
        {/* Preview table */}
        <TableConatienr>
          <Heading>选择特征</Heading>
          {/* For hiding preview table's border-right */}
          <div style={{ marginRight: -2 }}>
            <StructDataPreviewTable
              data={previewDataQuery.data?.data}
              loading={previewDataQuery.isFetching}
              checkable
              checkedKeys={checkedKeys}
              onCheckedChange={onCheckedChange}
            />
          </div>
        </TableConatienr>
        {/* Selected */}
        <SelectedConatienr>
          {!_validate(checkedFeats) && <InvalidAlert content="请检查特征缺失默认填充情况" banner />}
          <SelectedFeatCol>
            <Heading>已选 {0} 项特征</Heading>
            {checkedFeats.map((item) => {
              return (
                <FeatureDisplay key={item.key}>
                  {item.key}
                  <Tooltip content="取消选择该特征">
                    <Delete onClick={() => onFeatDeselect(item.key)} />
                  </Tooltip>
                </FeatureDisplay>
              );
            })}
          </SelectedFeatCol>
          <MissingCountCol>
            <Heading>缺失值填充</Heading>
            {checkedFeats.map((item) => {
              const isCustom = _isCustomType(item.value);
              return (
                <FeatureInput
                  type="number"
                  addBefore={
                    <Select
                      style={{ minWidth: 90 }}
                      defaultValue={isCustom ? CUSTOM_VALUE_TYPE : item.value}
                      onChange={(type) => onValueTypeChange({ type, key: item.key })}
                    >
                      {VALUE_TYPE_OPTIONS.map((item) => (
                        <Select.Option key={item.value} disabled={item.disabled} value={item.value}>
                          {item.label}
                        </Select.Option>
                      ))}
                    </Select>
                  }
                  defaultValue={item.value}
                  disabled={!isCustom}
                  placeholder="请输入"
                  onChange={(value: string, evt) =>
                    onFeatValueChange({ value: evt.target.value, key: item.key })
                  }
                  key={item.key}
                />
              );
            })}
          </MissingCountCol>

          {/* Nothing selected */}
          {nothingChecked && (
            <NoResultContainer>
              <NoResult width="200px" text="没有已选的特征" />
            </NoResultContainer>
          )}

          <ButtonGroup justify="center" gap={12}>
            <Button
              style={{ width: '156px' }}
              disabled={nothingChecked}
              onClick={onSubmit}
              type="primary"
            >
              下一步
            </Button>
            <Button onClick={onPreviousClick}>上一步</Button>
          </ButtonGroup>
        </SelectedConatienr>
      </Container>
    </ErrorBoundary>
  );

  function onSubmit(evt: Event) {
    if (checkedFeats.length === 0) {
      Message.error('请选择至少一个特征');
      evt.preventDefault();
      return;
    }
    if (!_validate(checkedFeats)) {
      Message.error('请检查特征缺失默认填充情况');
      evt.preventDefault();
      return;
    }
  }
  function onFeatDeselect(featKey: string) {
    const nextCheckedKeys = [...checkedKeys];

    nextCheckedKeys.splice(nextCheckedKeys.indexOf(featKey), 1);
    onCheckedChange(nextCheckedKeys);
  }
  function onValueTypeChange(payload: { type: string; key: string }) {
    if (payload.type !== CUSTOM_VALUE_TYPE) {
      updateValueByFeatKey(payload.key, payload.type);
    }
  }
  function onFeatValueChange(payload: { value: string; key: string }) {
    clearTimeout((inputTimer as unknown) as number);

    inputTimer = setTimeout(() => {
      updateValueByFeatKey(payload.key, payload.value);
    }, 200);
  }
  function updateValueByFeatKey(featKey: string, value: string) {
    const targetFeat = checkedFeats.find((item) => item.key === featKey);
    if (!targetFeat) return;

    targetFeat.value = value;

    onChange?.(_assembleValue(checkedFeats));
  }
  function onCheckedChange(keys: string[]) {
    const values = keys.map((key) => {
      return {
        key,
        value: checkedFeats.find((item) => item.key === key)?.value ?? '',
      };
    });
    onChange?.(_assembleValue(values));
  }
  function onPreviousClick() {}
};

/** Every featrure need a non-empty value */
function _validate(feats: ParsedFeatures) {
  return feats.every(({ value }) => Boolean(value.trim()));
}
/**
 * ! @NOTE: value is a twice-JSON-stringified string
 */
function _parseValue(value?: string): ParsedFeatures {
  if (!value) return [];

  try {
    const unwrapValue = JSON.parse(value);
    const featuresMap = unwrapValue?.replace ? JSON.parse(unwrapValue.replace(/\\/g, '')) : {};
    return Object.entries(featuresMap).map(([key, value]) => ({ key, value: value as string }));
  } catch (error) {
    console.error('[Feature Select]:', error);
    return [];
  }
}
/** ! @NOTE: Stringify twice warning */
function _assembleValue(feats: ParsedFeatures) {
  const data = JSON.stringify(Object.fromEntries(feats.map((item) => [item.key, item.value])));
  // NOTE: escape json string to avoid invalid params in backend
  return JSON.stringify(data);
}
/** Custom value is always number format */
function _isCustomType(val: string) {
  return /[\d]+/.test(val) || !val;
}
export default FeatureSelect;
