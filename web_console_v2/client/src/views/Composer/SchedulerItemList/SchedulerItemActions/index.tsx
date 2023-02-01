import React, { FC } from 'react';
import GridRow from 'components/_base/GridRow';
import { SchedulerItem } from 'typings/composer';
import SchedulerPipelineDrawer from '../../components/SchedulerPipelineDrawer';
import { useToggle } from 'react-use';

type Props = {
  scheduler: SchedulerItem;
};

const SchedulerItemActions: FC<Props> = ({ scheduler }) => {
  const [pipelineVisible, setPipelineVisible] = useToggle(false);
  const code = JSON.stringify(scheduler.pipeline, null, 2);
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
          pipeline
        </button>
        {/* <MoreActions actionList={actionList} /> */}
      </GridRow>
      <SchedulerPipelineDrawer
        title={<span>pipeline</span>}
        visible={pipelineVisible}
        onClose={setPipelineVisible}
        code={code}
      />
    </>
  );
};

export default SchedulerItemActions;
