import React, { FC, useMemo } from 'react';
import GridRow from 'components/_base/GridRow';
import { SchedulerRunner } from 'typings/composer';
import SchedulerPipelineDrawer from '../../components/SchedulerPipelineDrawer';
import { useToggle } from 'react-use';

type Props = {
  scheduler: SchedulerRunner;
};

const SchedulerItemActions: FC<Props> = ({ scheduler }) => {
  const [pipelineVisible, setPipelineVisible] = useToggle(false);
  const codeString = useMemo(() => {
    if (!scheduler) return '';
    const { pipeline, output, context } = scheduler;
    return JSON.stringify(
      {
        pipeline,
        context,
        output,
      },
      null,
      2,
    );
  }, [scheduler]);
  return (
    <>
      <GridRow>
        <button
          className="custom-text-button"
          style={{
            marginRight: 10,
          }}
          type="button"
          onClick={setPipelineVisible}
        >
          数据详情
        </button>
        {/* <MoreActions actionList={actionList} /> */}
      </GridRow>
      <SchedulerPipelineDrawer
        title={<span>数据详情</span>}
        visible={pipelineVisible}
        onClose={setPipelineVisible}
        code={codeString}
      />
    </>
  );
};

export default SchedulerItemActions;
