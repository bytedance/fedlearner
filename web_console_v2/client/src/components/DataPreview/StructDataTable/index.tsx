/* istanbul ignore file */

import React, { FC, memo, useRef, useMemo } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { isEmpty, isNil, floor } from 'lodash-es';

import { Table, Spin, Checkbox } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import NoResult from 'components/NoResult';

import { PreviewData, ValueType } from 'typings/dataset';
import { TABLE_COL_WIDTH } from 'shared/constants';

const Container = styled.div`
  ${(props: any) =>
    props.activeIndex === 1
      ? ''
      : `.arco-table-th:nth-child(${props.activeIndex}), .arco-table-td:nth-child(${props.activeIndex}) {
            --activeBackground: rgba(22, 100, 255, 0.06);
            --summaryBackground: transparent;
          }`}
`;

const PreviewTable = styled(Table)`
  border: 1px solid var(--lineColor);
  border-radius: 4px;
  width: auto;

  .arco-table-th-item,
  .arco-table-td {
    padding: 0;
  }

  .arco-table-col-fixed-left:first-of-type {
    text-align: center;
    background: var(--color-fill-2);
  }

  .arco-table-cell {
    word-break: break-word;
  }
`;
const SummaryCol = styled.div`
  padding: 8px;
  font-size: 12px;
  line-height: 22px;
  white-space: nowrap;
  background-color: var(--summaryBackground, #ffffff) !important;
`;
const SummaryLabelCol = styled(SummaryCol)`
  margin-left: -40px;
  padding-left: 30px;
`;
const SummaryColCell = styled.div``;
const DataTypeCell = styled(SummaryColCell)`
  color: var(--textColorSecondary);
`;
const ClickableHeader = styled.label`
  display: flex;
  padding: 8px;
  font-size: 12px;
  text-decoration: underline;
  white-space: nowrap;
  cursor: pointer;
  border-right: 1px solid var(--lineColor);
  border-bottom: 2px solid var(--lineColor);
  background-color: #ffffff;

  &[data-is-avtive='true'] {
    background-color: var(--activeBackground) !important;
    box-shadow: 0 2.5px 0 0 var(--primaryColor) inset;
  }

  &:hover {
    color: var(--primaryColor);
  }
`;

const TableCell = styled.label`
  display: flex;
  padding: 12px 8px;
  font-size: 12px;
  &[data-is-avtive='true'] {
    background-color: var(--activeBackground);
  }
`;

const SummaryTd = styled.td`
  background-color: #fafafa;
  text-align: center;
`;
const CheckboxConatiner = styled.div`
  margin-left: 5px;
  transform: scale(0.875);
`;

export const STRUCT_DATA_TABLE_ID = 'struct_data_table';

/**
 * Format origin value to display value
 */
export function formatOriginValue(originValue: string | number, type?: ValueType) {
  if (type === 'string') {
    return originValue;
  }
  /**
   * origin value  /  display value
   * missing value => "null"
   * string "null" => "null"
   * string "nan"  => "NaN"
   */
  let displayValue: string | number;
  if (originValue == null || originValue === 'null') {
    displayValue = 'null';
  } else if (originValue === 'nan') {
    displayValue = 'NaN';
  } else {
    displayValue = parseFloat(Number(originValue).toFixed(3));
  }
  return displayValue;
}

const FeatureMetric: FC<{
  type?: string;
  missingCount?: string | number;
  baseMissingCount?: string | number;
  count?: string | number;
  baseCount?: string | number;
}> = memo(({ type, missingCount, baseMissingCount, count, baseCount }) => {
  let tempMissingCount = 0;
  let tempAllCount = 0;
  let missingRate = 'N/A';

  let tempBaseMissingCount = 0;
  let tempBaseAllCount = 0;
  let baseMissingRate = 'N/A';

  if (missingCount !== 'N/A') {
    tempMissingCount = Number(missingCount) || 0;
    tempAllCount = tempMissingCount + (Number(count) || 0);
    missingRate = floor((tempMissingCount / tempAllCount) * 100, 2) + '%';
  }
  if (baseMissingCount !== 'N/A') {
    tempBaseMissingCount = Number(baseMissingCount) || 0;
    tempBaseAllCount = tempBaseMissingCount + (Number(baseCount) || 0);
    baseMissingRate = floor((tempBaseMissingCount / tempBaseAllCount) * 100, 2) + '%';
  }

  return (
    <SummaryCol>
      <DataTypeCell>{type}</DataTypeCell>
      {baseMissingCount && <SummaryColCell>{baseMissingRate}</SummaryColCell>}
      <SummaryColCell>{missingRate}</SummaryColCell>
    </SummaryCol>
  );
});

const CustomRow: React.FC<{ index: number; maxCount: number; featuresKeysCount: number }> = (
  props,
) => {
  const { index, maxCount, featuresKeysCount, children, ...restProps } = props;

  // Render summary row
  if (index >= maxCount) {
    return (
      <tr {...restProps}>
        <SummaryTd colSpan={featuresKeysCount + 1}>
          <span>以上为取 {maxCount.toLocaleString('en')} 条样本数据</span>
        </SummaryTd>
      </tr>
    );
  }

  return <tr children={children} {...restProps} />;
};

type Props = {
  data?: PreviewData;
  loading?: boolean;
  compareWithBase?: boolean;
  baseData?: PreviewData;
  datasetName?: string;
  activeKey?: string;
  checkable?: boolean;
  checkedKeys?: string[];
  noResultText?: string;
  isError?: boolean;
  onCheckedChange?: (keys: string[]) => void;
  onActiveFeatChange?: (k: string) => void;
};

const StructDataPreviewTable: FC<Props> = ({
  datasetName = '',
  loading,
  data,
  baseData,
  activeKey,
  onActiveFeatChange,
  compareWithBase,
  checkable,
  checkedKeys = [],
  onCheckedChange,
  noResultText,
  isError,
}) => {
  const dom = useRef<HTMLDivElement>();
  const { t } = useTranslation();

  const [featuresKeys, featuresTypes] = useMemo(() => {
    const featuresKeys: string[] = [];
    const featuresTypes: ValueType[] = [];

    data?.dtypes?.forEach((item) => {
      featuresKeys.push(item.key);
      featuresTypes.push(item.value);
    });

    return [featuresKeys, featuresTypes];
  }, [data]);

  if (isError) {
    return <NoResult text={t('dataset.tip_state_error')} />;
  }

  if (loading) {
    return (
      <GridRow style={{ height: '100%' }} justify="center">
        <Spin loading={true} />
      </GridRow>
    );
  }
  if (isNil(data)) {
    return <NoResult text={t('dataset.tip_state_error')} />;
  }

  const previewData = data;

  const metrics = previewData.metrics ?? {};
  const count = previewData.count ?? 0;
  const sampleCount = previewData.sample?.length ?? 0;

  if (noResultText) {
    return <NoResult text={noResultText} />;
  }

  if (!previewData.sample || isEmpty(previewData.sample)) {
    return <NoResult text={t('dataset.tip_state_error')} />;
  }

  if (!previewData.metrics || isEmpty(previewData.metrics)) {
    return <NoResult text={t('dataset.tip_state_error')} />;
  }

  const list = previewData.sample.map((item) => {
    return item.reduce((ret, curr, index) => {
      ret[featuresKeys[index] as any] = formatOriginValue(curr, featuresTypes[index]);
      return ret;
    }, {} as { [key: string]: string | number });
  });

  const isShowSummaryRow = list.length > 0 && list.length < count;

  // Add summary row
  if (isShowSummaryRow) {
    list.push({
      id: '__summary__',
    });
  }

  const activeKeyIndex = featuresKeys.indexOf(activeKey!);
  const headerCellStyle = {
    padding: 0,
  };
  const columns: any[] = [
    {
      fixed: 'left',
      children: [
        {
          title: (
            <SummaryLabelCol className="head-col">
              <DataTypeCell>类型</DataTypeCell>
              {compareWithBase && <SummaryColCell>原始数据集缺失率%</SummaryColCell>}
              <SummaryColCell>{compareWithBase && datasetName}缺失率%</SummaryColCell>
            </SummaryLabelCol>
          ),
          fixed: 'left',
          width: TABLE_COL_WIDTH.THIN,
          dataIndex: 'order',
          key: 'order',
          headerCellStyle: {
            ...headerCellStyle,
            backgroundColor: '#fff',
          },
          render: (_: any, record: any, index: number) => {
            return <span>{index + 1}</span>;
          },
        },
      ],
      headerCellStyle: {
        ...headerCellStyle,
        backgroundColor: '#fff',
        backgroundImage: `url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAMCAYAAABWdVznAAAANklEQVR4AZXKBQ3AQBTA0Lke8ybimz2sgjZp8A2m6Y9T4eWLrHBbYBaYBWaBWWAWmAVmgVlgLvftw6nDSDtTAAAAAElFTkSuQmCC')`,
        backgroundSize: '8px 8px',
        backgroundPosition: 'right bottom',
        backgroundRepeat: 'no-repeat',
      },
    },
    ...featuresKeys.map((featKey, index) => ({
      key: featKey,
      headerCellStyle,
      title: (
        <ClickableHeader
          data-is-avtive={activeKey === featKey}
          onClick={() => onFeatColHeaderClick(featKey)}
        >
          {featKey}
          {checkable && (
            <CheckboxConatiner>
              <Checkbox
                checked={checkedKeys.includes(featKey)}
                onChange={(checked) => onFeatChecked(featKey, checked)}
              />
            </CheckboxConatiner>
          )}
        </ClickableHeader>
      ),
      children: [
        {
          width: Math.max(featKey.length, 7) * 10 + (checkable ? 20 : 0),
          headerCellStyle,
          title: (
            <FeatureMetric
              type={featuresTypes[index]}
              missingCount={metrics[featKey]?.missing_count ?? 0}
              baseMissingCount={
                compareWithBase
                  ? (baseData?.metrics && baseData.metrics[featKey]?.missing_count) ?? 'N/A'
                  : undefined
              }
              baseCount={
                compareWithBase
                  ? (baseData?.metrics && baseData.metrics[featKey]?.count) ?? 'N/A'
                  : undefined
              }
              count={metrics[featKey]?.count ?? 0}
            />
          ),
          key: featKey,
          dataIndex: featKey,
          render: (value: any, record: any, index: number) => {
            return renderColumn(value, index, activeKey === featKey);
          },
        },
      ],
    })),
  ];

  return (
    <Container
      id={STRUCT_DATA_TABLE_ID}
      ref={(dom as unknown) as any}
      {...{ activeIndex: activeKeyIndex + 2 }}
    >
      <PreviewTable
        data={list}
        columns={columns}
        size="small"
        pagination={false}
        scroll={{
          x: 'max-content',
          y: window.innerHeight - 490,
        }}
        components={{
          body: {
            row: CustomRow,
          },
        }}
        onRow={(record, index) => {
          return {
            index,
            // Set 999999, in order to don't show summary row
            maxCount: isShowSummaryRow ? sampleCount : 999999,
            featuresKeysCount: featuresKeys.length,
          } as any;
        }}
      />
    </Container>
  );

  function renderColumn(value: string, index: number, isActive: boolean) {
    const obj = {
      children: <TableCell data-is-avtive={isActive}>{value}</TableCell>,
      props: {} as any,
    };
    // Last column of each row consist the summary row on the bottom
    if (isShowSummaryRow && index === sampleCount) {
      obj.props.colSpan = 0;
    }
    return obj;
  }

  function onFeatColHeaderClick(featKey: string) {
    onActiveFeatChange?.(featKey);
  }
  function onFeatChecked(key: string, checked: boolean) {
    if (!checkable) return;

    const nextCheckedKeys = [...checkedKeys];
    if (checked) {
      nextCheckedKeys.push(key);
    } else {
      nextCheckedKeys.splice(nextCheckedKeys.indexOf(key), 1);
    }
    onCheckedChange?.(nextCheckedKeys);
  }
};

export default StructDataPreviewTable;
