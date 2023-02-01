/* istanbul ignore file */

import React, { FC, useMemo, useState } from 'react';
import styled from 'styled-components';
import i18n from 'i18n';
import { Switch } from '@arco-design/web-react';
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
`;
const Content = styled.div`
  position: relative;
  width: 160px;
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  margin: 0 auto;
`;

const Item = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 0 0 80px;
  width: 80px;
  height: 50px;
  font-size: 12px;
  &:nth-of-type(1) {
    background-color: #468dff;
    color: #fff;
  }
  &:nth-of-type(2) {
    background-color: #f6f9fe;
    color: var(--textColor);
  }
  &:nth-of-type(3) {
    background-color: #d6e4fd;
    color: var(--textColor);
  }
  &:nth-of-type(4) {
    background-color: #7da9f8;
    color: #fff;
  }
`;

const Label = styled.span`
  font-size: 12px;
  color: var(--textColorStrong);
`;
const TopTitle = styled(Label)`
  display: block;
  width: 100%;
  margin-bottom: 10px;
  text-align: center;
`;
const LeftTitle = styled(Label)`
  position: absolute;
  top: 65px;
  left: -45px;
  transform: rotate(-90deg);
`;
const RightTopTitle = styled(Label)`
  position: absolute;
  top: 45px;
  right: -30px;
`;
const RightBottomTitle = styled(Label)`
  position: absolute;
  top: 95px;
  right: -30px;
`;
const BottomLeftTitle = styled(Label)`
  position: absolute;
  bottom: 15px;
  left: 30px;
`;
const BottomRightTitle = styled(Label)`
  position: absolute;
  bottom: 15px;
  right: 30px;
`;

const Bar = styled.div`
  position: relative;
  width: 160px;
  height: 8px;
  margin-top: 30px;
  background: linear-gradient(90deg, #fff 0%, #468dff 100%);
  visibility: hidden;
  &::before {
    position: absolute;
    left: -30px;
    top: -5px;
    display: inline-block;
    content: '0';
    font-size: 12px;
    color: var(--textColorStrong);
  }
  &::after {
    position: absolute;
    top: -5px;
    right: -30px;
    display: inline-block;
    content: '1';
    font-size: 12px;
    color: var(--textColorStrong);
  }
`;

const CenterLayout = styled.div`
  margin: 0 auto;
`;

const Title = styled(TitleWithIcon)`
  position: absolute;
  left: 16px;
  top: 12px;
  color: var(--textColor);
  font-size: 12px;
`;

const PercentContainer = styled.div`
  position: absolute;
  top: -3px;
  right: -80px;

  button {
    margin-left: 10px;
  }
`;

export type Props = {
  valueList: any[];
  percentValueList?: any[];
  height?: number;
  title?: string;
  tip?: string;
  isEmpty?: boolean;
  formatPercentValueList?: (valueList: number[]) => string[];
};

export type ModelEvaluationVariantProps = {
  id: ID;
  participantId?: ID;
};

export const defaultFormatPercentValueList = (valueList: number[]) => {
  const total = valueList.reduce((acc: number, cur: number) => acc + cur, 0);
  return valueList.map((num) => ((num / total) * 100).toFixed(2) + '%');
};

type VariantComponents = {
  ModelEvaluationVariant: React.FC<ModelEvaluationVariantProps>;
};

export const ConfusionMatrix: FC<Props> & VariantComponents = ({
  valueList,
  percentValueList: percentValueListFromProps,
  height = 260,
  title = 'Confusion matrix',
  tip = '',
  isEmpty = false,
  formatPercentValueList = defaultFormatPercentValueList,
}) => {
  const [isShowPercent, setIsShowPercent] = useState(false);

  const percentValueList = useMemo(() => {
    if (percentValueListFromProps) {
      return percentValueListFromProps;
    }

    if (!valueList) {
      return [];
    }

    return formatPercentValueList(valueList);
  }, [valueList, percentValueListFromProps, formatPercentValueList]);

  const displayValueList = isShowPercent ? percentValueList : valueList;

  // tp = true positive，答案是1、预测是1
  // tn = true negative，答案是0、预测是0
  // fp = false positive，预测是1，答案是0
  // fn = false negative，预测是0，答案是1
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
      {isEmpty ? (
        <CenterLayout style={{ margin: '0 auto' }}>
          <NoResult.NoData />
        </CenterLayout>
      ) : (
        <Content>
          <TopTitle>Actual class</TopTitle>
          <LeftTitle>Predicted</LeftTitle>
          <RightTopTitle>0</RightTopTitle>
          <RightBottomTitle>1</RightBottomTitle>
          <BottomLeftTitle>0</BottomLeftTitle>
          <BottomRightTitle>1</BottomRightTitle>
          <LeftTitle>Predicted</LeftTitle>
          <Item>{displayValueList?.[3] ?? ''}</Item>
          <Item>{displayValueList?.[1] ?? ''}</Item>
          <Item>{displayValueList?.[2] ?? ''}</Item>
          <Item>{displayValueList?.[0] ?? ''}</Item>
          <PercentContainer>
            <TitleWithIcon
              title={i18n.t('model_center.title_confusion_matrix_normalization')}
              isShowIcon={true}
              isBlock={false}
              tip={i18n.t('model_center.tip_confusion_matrix_normalization')}
              icon={QuestionCircle}
            />
            <Switch checked={isShowPercent} onChange={onSwitchChange} />
          </PercentContainer>
          <Bar />
        </Content>
      )}
    </Card>
  );

  function onSwitchChange(val: boolean) {
    setIsShowPercent(val);
  }
};

export const ModelEvaluationVariant: React.FC<ModelEvaluationVariantProps> = ({
  id,
  participantId,
}) => {
  const { data } = useModelMetriesResult(id, participantId);

  const valueList = useMemo(() => {
    if (!data) {
      return [];
    }
    const { confusion_matrix = {} } = data;
    return [confusion_matrix.tp, confusion_matrix.fn, confusion_matrix.fp, confusion_matrix.tn].map(
      (item) => {
        switch (typeof item) {
          case 'string':
            return parseInt(item);
          case 'number':
            return item;
          case 'undefined':
          default:
            return 0;
        }
      },
    );
  }, [data]);

  return (
    <ConfusionMatrix
      valueList={valueList}
      isEmpty={valueList.length === 0 || valueList.every((v) => v === 0)}
    />
  );
};

ConfusionMatrix.ModelEvaluationVariant = ModelEvaluationVariant;

export default ConfusionMatrix;
