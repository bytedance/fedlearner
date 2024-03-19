import React, { ReactElement } from 'react';
import styles from './index.module.less';
import { Progress, ProgressProps, Tooltip, TooltipProps } from '@arco-design/web-react';
interface Props extends ProgressProps {
  statusText: string;
  toolTipPosition?: TooltipProps['position'];
  toolTipContent?: TooltipProps['content'];
}
function ProgressWithText({
  style,
  className,
  percent,
  status,
  statusText,
  toolTipPosition = 'top',
  toolTipContent,
  ...props
}: Props): ReactElement {
  return (
    <Tooltip position={toolTipPosition} content={toolTipContent}>
      <div className={`${styles.progress_container} ${className}`} style={style}>
        <span className={styles.progress_name}>{statusText ?? '-'}</span>
        <Progress
          percent={percent ?? 100}
          status={status ?? 'normal'}
          showText={false}
          trailColor="var(--color-primary-light-1)"
        />
      </div>
    </Tooltip>
  );
}
export default ProgressWithText;
