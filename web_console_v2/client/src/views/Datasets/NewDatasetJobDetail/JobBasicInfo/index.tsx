import React, { useMemo } from 'react';
import { formatTimestamp } from 'shared/date';
import PropertyList from 'components/PropertyList';
import WhichParticipant from 'components/WhichParticipant';
import styled from './index.module.less';

type TJobBasicInfo = {
  coordinatorId: ID;
  createTime: DateTime;
  creator_username: string;
};

export default function JobBasicInfo(prop: TJobBasicInfo) {
  const { coordinatorId, createTime = 0, creator_username } = prop;
  const basicInfo = useMemo(() => {
    function TimeRender(prop: { time: DateTime }) {
      const { time } = prop;
      return <span>{time <= 0 ? '-' : formatTimestamp(time)}</span>;
    }
    return [
      {
        label: '任务发起方',
        value: coordinatorId === 0 ? '本方' : <WhichParticipant id={coordinatorId} />,
      },
      {
        label: '创建者',
        value: creator_username,
      },
      {
        label: '创建时间',
        value: <TimeRender time={createTime} />,
      },
    ];
  }, [coordinatorId, createTime, creator_username]);
  return (
    <div className={styled.job_basic_info}>
      <PropertyList properties={basicInfo} cols={4} />
    </div>
  );
}
