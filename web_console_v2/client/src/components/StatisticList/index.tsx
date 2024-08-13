/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import styled from 'styled-components';

import { Card, Empty } from '@arco-design/web-react';
import TitleWithIcon, { Props as TitleWithIconProps } from 'components/TitleWithIcon';
import { IconQuestionCircle } from '@arco-design/web-react/icon';
import { CONSTANTS } from 'shared/constants';
import { formatObjectToArray } from 'shared/helpers';
import { useModelMetriesResult } from 'hooks/modelCenter';

const Container = styled.div`
  display: inline-block;
`;

const Label = styled.div`
  font-weight: 500;
  font-size: 20px;
  color: var(--textColorStrong);
`;

type NumberItemProps = {
  value?: string | number;
  className?: string;
} & TitleWithIconProps;

type ModelEvaluationVariantProps = {
  id: ID;
  participantId?: ID;
  isTraining?: boolean;
};

export const NumberItem: FC<NumberItemProps> = ({
  className,
  value = CONSTANTS.EMPTY_PLACEHOLDER,
  ...props
}) => {
  return (
    <Container className={className}>
      <TitleWithIcon isShowIcon={Boolean(props.tip)} icon={IconQuestionCircle} {...props} />
      <Label>{value}</Label>
    </Container>
  );
};

const CardContainer = styled.div`
  display: flex;
  justify-content: flex-start;
  flex-wrap: wrap;
`;
const StyledNumberItem = styled(NumberItem)<{ $cols: number }>`
  width: ${(props) => String(100 / props.$cols) + '%'};
`;

export type OptionItem = {
  /** Display title */
  text: string;
  /** Display value */
  value: string | number;
  /** Tip */
  tip?: string;
};

export type Props = {
  /** DataSource */
  data: OptionItem[];
  /** How many cols in one row */
  cols?: number;
};

export type SubComponent = {
  ModelEvaluation: FC<ModelEvaluationVariantProps>;
};

export const StatisticList: FC<Props> & SubComponent = ({ data, cols = 6 }) => {
  return (
    <Card>
      <CardContainer>
        {data.length > 0 ? (
          data.map((item) => (
            <StyledNumberItem
              $cols={cols}
              key={item.text}
              title={item.text}
              value={item.value}
              tip={item.tip}
              isShowIcon={Boolean(item.tip)}
              icon={IconQuestionCircle}
            />
          ))
        ) : (
          <Empty />
        )}
      </CardContainer>
    </Card>
  );
};

const sortingKeys = [
  'acc',
  'auc',
  'precision',
  'recall',
  'f1',
  'ks',
  'mse',
  'msre',
  'abs',
  'loss',
  'tp',
  'tn',
  'fp',
  'fn',
];

const labelKeyMap: Record<string, string> = {
  loss: 'LOSS',
  f1: 'F1 score',
  auc: 'AUC',
  acc: 'Accuracy',
  precision: 'Precision',
  recall: 'Recall',
};
export const ModelEvaluation: FC<ModelEvaluationVariantProps> = ({
  id,
  participantId,
  isTraining = true,
}) => {
  const { data } = useModelMetriesResult(id, participantId);

  const list = useMemo(() => {
    if (!data) {
      return [];
    }

    return formatObjectToArray(isTraining ? data.train : data.eval, sortingKeys).map(
      ({ label, value }) => ({
        text: labelKeyMap[label] ?? label.toUpperCase(),
        value: value.values?.length
          ? value.values[value.values.length - 1]?.toFixed(3)
          : CONSTANTS.EMPTY_PLACEHOLDER,
      }),
    );
  }, [data, isTraining]);

  return <StatisticList data={list} />;
};

StatisticList.ModelEvaluation = ModelEvaluation;

export default StatisticList;
