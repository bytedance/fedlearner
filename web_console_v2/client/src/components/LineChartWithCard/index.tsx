/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import styled from 'styled-components';

import LineChart from 'components/LineChart';
import NoResult from 'components/NoResult';
import TitleWithIcon from 'components/TitleWithIcon';
import { QuestionCircle } from 'components/IconPark';
import { useModelMetriesResult } from 'hooks/modelCenter';
import { formatTimestamp } from 'shared/date';
import { Space } from '@arco-design/web-react';

const Card = styled.div<{ height?: number }>`
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  ${(props) => props.height && `height: ${props.height}px`};
  border: 1px solid var(--lineColor);
  border-radius: 2px;
  padding: 30px 16px;
`;
const Title = styled(TitleWithIcon)`
  position: absolute;
  left: 16px;
  top: 12px;
  color: var(--textColor);
  font-size: 12px;
`;
const Content = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  margin: 0 auto;
`;
type Item = {
  label: string;
  value: any;
};

export type Props = {
  valueList: Item[];
  height?: number;
  title?: string;
  tip?: string;
};

export type ModelMetricsProps = {
  id: ID;
  participantId?: ID;
  isTraining?: boolean;
};

type VariantComponent = {
  ModelMetrics: FC<ModelMetricsProps>;
};

export const LineChartWithCard: FC<Props> & VariantComponent = ({
  valueList = [],
  height = 260,
  title = 'Acc',
  tip = '',
}) => {
  return (
    <Card height={height}>
      <Title
        title={title || ''}
        isShowIcon={Boolean(tip)}
        isLeftIcon={false}
        isBlock={false}
        tip={tip}
        icon={QuestionCircle}
      />
      {valueList.length > 0 ? (
        <Content>
          <LineChart valueList={valueList} />
        </Content>
      ) : (
        <NoResult.NoData />
      )}
    </Card>
  );
};

const ModelMetrics: FC<ModelMetricsProps> = ({ id, participantId, isTraining = true }) => {
  const { data } = useModelMetriesResult(id, participantId);

  const metricsList = useMemo(() => {
    if (!data) {
      return [];
    }

    const list: Array<{
      label: string;
      valueList: Array<{
        label: string;
        value: number;
      }>;
    }> = [];
    const obj = (isTraining ? data.train : data.eval) ?? {};

    Object.keys(obj).forEach((key) => {
      const steps: number[] = obj[key]?.steps ?? [];
      const values: number[] = obj[key]?.values ?? [];

      list.push({
        label: key.toUpperCase(),
        valueList: steps.map((item, index) => {
          return {
            label: formatTimestamp(item),
            value: values[index] || 0,
          };
        }),
      });
    });

    return list;
  }, [data, isTraining]);

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      {metricsList.map((item) => {
        return <LineChartWithCard key={item.label} valueList={item.valueList} title={item.label} />;
      })}
    </Space>
  );
};

LineChartWithCard.ModelMetrics = ModelMetrics;
export default LineChartWithCard;
