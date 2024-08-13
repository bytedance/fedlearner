/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import styled from 'styled-components';

import HorizontalBarChart from 'components/HorizontalBarChart';
import NoResult from 'components/NoResult';
import TitleWithIcon from 'components/TitleWithIcon';
import { QuestionCircle } from 'components/IconPark';
import { useModelMetriesResult } from 'hooks/modelCenter';

const Card = styled.div<{ height?: number }>`
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  ${(props) => props.height && `height: ${props.height}px`};
  border: 1px solid var(--lineColor);
  border-radius: 2px;
  padding: 30px 0;
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

type TXTickFormatter = (val: number) => string | number;

function defaultXTickFormatter(val: any) {
  return val;
}

const getBarOption = (xTickFormatter?: TXTickFormatter) => {
  return {
    maintainAspectRatio: false,
    indexAxis: 'y',
    // Elements options apply to all of the options unless overridden in a dataset
    // In this case, we are setting the border of each horizontal bar to be 2px wide
    elements: {
      bar: {
        borderWidth: 0,
      },
    },
    responsive: true,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        grid: {
          color: 'transparent',
          tickColor: '#cecece',
        },
      },
      x: {
        grid: {
          drawBorder: false,
        },
        min: 0,
        ticks: {
          callback:
            typeof xTickFormatter === 'function'
              ? xTickFormatter
              : function (value: any) {
                  return value;
                },
        },
      },
    },
  };
};

type Item = {
  label: string;
  value: any;
};

export type Props = {
  valueList: Item[];
  height?: number;
  title?: string;
  tip?: string;
  xTipFormatter?: TXTickFormatter;
};

export type ModelEvaluationVariantProps = {
  id: ID;
  participantId?: ID;
  tip?: string;
};

type VariantComponent = {
  ModelEvaluationVariant: FC<ModelEvaluationVariantProps>;
};

export const FeatureImportance: FC<Props> & VariantComponent = ({
  valueList = [],
  height = 260,
  title = 'Feature importance（Top 15）',
  tip = 'Feature importance',
  xTipFormatter = defaultXTickFormatter,
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
          <HorizontalBarChart valueList={valueList} options={getBarOption(xTipFormatter)} />
        </Content>
      ) : (
        <NoResult.NoData />
      )}
    </Card>
  );
};

const ModelValuationVariant: FC<ModelEvaluationVariantProps> = ({ id, participantId, tip }) => {
  const { data } = useModelMetriesResult(id, participantId);

  const valueList = useMemo(() => {
    if (!data) {
      return [];
    }

    const list = [];
    const { feature_importance = {} } = data;

    for (const k in feature_importance) {
      list.push({
        label: k,
        value: feature_importance[k],
      });
    }
    return list.sort((a, b) => b.value - a.value);
  }, [data]);

  return <FeatureImportance valueList={valueList} xTipFormatter={(val: any) => val} tip={tip} />;
};

FeatureImportance.ModelEvaluationVariant = ModelValuationVariant;
export default FeatureImportance;
