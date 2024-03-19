import React, { CSSProperties, FC, useMemo, useState } from 'react';
import { Grid, Tabs, Space, Typography, Switch, Tooltip, Message } from '@arco-design/web-react';
import { toString } from 'lodash-es';
import StatisticList from 'components/StatisticList';
import ConfusionMatrix from 'components/ConfusionMatrix';
import FeatureImportance from 'components/FeatureImportance';
import LineChartWithCard from 'components/LineChartWithCard';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantList } from 'hooks';
import { EnumAlgorithmProjectType } from 'typings/algorithm';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import { updateModelJob } from 'services/modelCenter';

import styles from './ReportResult.module.less';

type Props = {
  id: ID;
  algorithmType?: EnumAlgorithmProjectType;
  title?: string;
  style?: CSSProperties;
  isTraining?: boolean;
  isNNAlgorithm?: boolean;
  hideConfusionMatrix?: boolean;
  metricIsPublic?: boolean;
  onSwitch?: () => void;
};

const ReportResult: FC<Props> = ({
  id,
  title,
  style,
  algorithmType,
  isTraining = true,
  isNNAlgorithm,
  hideConfusionMatrix = false,
  metricIsPublic = false,
  onSwitch,
}) => {
  const stringifyId = toString(id);

  const projectId = toString(useGetCurrentProjectId());
  const participantList = useGetCurrentProjectParticipantList();
  const [switchLoading, setSwitchLoading] = useState(false);
  const [resultTarget, setResultTarget] = useState<string>(stringifyId);
  const participantId = useMemo(() => {
    return resultTarget === stringifyId ? undefined : resultTarget;
  }, [resultTarget, stringifyId]);
  const handleOnChangeIsPublic = (checked: boolean) => {
    setSwitchLoading(true);
    updateModelJob(projectId, stringifyId, {
      metric_is_public: checked,
    }).then(
      (res) => {
        Message.success('编辑成功');
        setSwitchLoading(false);
        onSwitch && onSwitch();
      },
      (err) => {
        Message.error(err.message);
        setSwitchLoading(false);
      },
    );
  };

  return (
    <div style={style}>
      <Space className={styles.space_container}>
        <Typography.Text className="custom-typography" bold={true}>
          {title ?? '评估报告'}
        </Typography.Text>
        <Tabs
          className="custom-tabs"
          type="text"
          activeTab={resultTarget}
          onChange={setResultTarget}
        >
          <Tabs.TabPane title="本方" key={stringifyId} />
          {(isTraining || algorithmType !== EnumAlgorithmProjectType.NN_HORIZONTAL) &&
            (participantList ?? []).map((peer: any) => (
              <Tabs.TabPane title={peer.name} key={toString(peer.id)} />
            ))}
        </Tabs>
        {(isTraining || algorithmType !== EnumAlgorithmProjectType.NN_HORIZONTAL) && (
          <Space>
            共享训练报告
            <Tooltip content={'开启后，将与合作伙伴共享本次训练指标'}>
              <IconInfoCircle />
            </Tooltip>
            <Switch
              loading={switchLoading}
              checked={metricIsPublic}
              onChange={handleOnChangeIsPublic}
            />
          </Space>
        )}
      </Space>
      <Space direction="vertical" style={{ width: '100%' }}>
        <StatisticList.ModelEvaluation
          id={stringifyId}
          participantId={participantId}
          isTraining={isTraining}
        />
        {isNNAlgorithm ? (
          <LineChartWithCard.ModelMetrics
            id={stringifyId}
            participantId={participantId}
            isTraining={isTraining}
          />
        ) : (
          <Grid.Row gutter={20}>
            {!hideConfusionMatrix && (
              <Grid.Col span={12}>
                <ConfusionMatrix.ModelEvaluationVariant
                  id={stringifyId}
                  participantId={participantId}
                />
              </Grid.Col>
            )}
            <Grid.Col span={hideConfusionMatrix ? 24 : 12}>
              <FeatureImportance.ModelEvaluationVariant
                tip={'数值越高，表示该特征对模型的影响越大'}
                id={stringifyId}
                participantId={participantId}
              />
            </Grid.Col>
          </Grid.Row>
        )}
      </Space>
    </div>
  );
};

export default ReportResult;
