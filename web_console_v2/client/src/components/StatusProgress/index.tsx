import React, { FC, useMemo } from 'react';
import { Progress, Tooltip } from '@arco-design/web-react';
import styled from './index.module.less';

type Option = {
  status: string;
  text: string;
  color: string;
  percent: number;
};
type Props = {
  options: Option[];
  status: string;
  isTip?: boolean;
  toolTipContent?: React.ReactNode;
  className?: string;
};

const defaultStatus: Option = {
  status: 'DEFAULT',
  text: '未知',
  color: '#165DFF',
  percent: 0,
};

const StatusProgress: FC<Props> = ({
  options,
  status,
  isTip = false,
  toolTipContent,
  className,
}) => {
  const currentStatus = useMemo(() => {
    return options.find((option) => option.status === status) || defaultStatus;
  }, [status, options]);
  if (isTip) {
    return (
      <Tooltip content={toolTipContent}>
        <div className={`${styled.status_progress} ${className}`}>
          <span className={styled.status_progress_text}>{currentStatus.text}</span>
          <Progress
            color={currentStatus?.color}
            percent={currentStatus?.percent || 0}
            showText={false}
          />
        </div>
      </Tooltip>
    );
  }
  return (
    <div className={`${styled.status_progress} ${className}`}>
      <span className={styled.status_progress_text}>{currentStatus.text}</span>
      <Progress
        color={currentStatus?.color}
        percent={currentStatus?.percent || 0}
        showText={false}
      />
    </div>
  );
};

export default StatusProgress;
