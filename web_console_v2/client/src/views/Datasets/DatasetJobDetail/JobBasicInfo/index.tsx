import React, { useMemo } from 'react';
import { formatTimeCount, formatTimestamp } from 'shared/date';
import PropertyList from 'components/PropertyList';
import WhichParticipant from 'components/WhichParticipant';
import { DatasetJobState } from 'typings/dataset';
import dayjs from 'dayjs';
import CountTime from 'components/CountTime';

type TJobBasicInfo = {
  coordinatorId: ID;
  createTime: DateTime;
  startTime: DateTime;
  finishTime: DateTime;
  jobState: DatasetJobState;
};

export default function JobBasicInfo(prop: TJobBasicInfo) {
  const { coordinatorId, createTime = 0, startTime = 0, finishTime = 0, jobState } = prop;
  const isRunning = [DatasetJobState.PENDING, DatasetJobState.RUNNING].includes(jobState);
  const basicInfo = useMemo(() => {
    function TimeRender(prop: { time: DateTime }) {
      const { time } = prop;
      return <span>{time <= 0 ? '-' : formatTimestamp(time)}</span>;
    }
    function RunningTimeRender(prop: { start: DateTime; finish: DateTime; isRunning: boolean }) {
      const { start, finish, isRunning } = prop;
      if (isRunning) {
        return start <= 0 ? (
          <span>待运行</span>
        ) : (
          <CountTime time={dayjs().unix() - start} isStatic={false} />
        );
      }
      return <span>{finish - start <= 0 ? '-' : formatTimeCount(finish - start)}</span>;
    }
    return [
      {
        label: '任务发起方',
        value: coordinatorId === 0 ? '本方' : <WhichParticipant id={coordinatorId} />,
      },
      {
        label: '创建时间',
        value: <TimeRender time={createTime} />,
      },
      {
        label: '开始时间',
        value: <TimeRender time={startTime} />,
      },
      {
        label: '结束时间',
        value: <TimeRender time={finishTime} />,
      },
      {
        label: '运行时长',
        value: <RunningTimeRender start={startTime} finish={finishTime} isRunning={isRunning} />,
      },
    ];
  }, [coordinatorId, createTime, startTime, finishTime, isRunning]);
  return <PropertyList properties={basicInfo} cols={5} />;
}
