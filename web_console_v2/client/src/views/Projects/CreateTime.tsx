import React, { ReactElement, CSSProperties } from 'react';
import { formatTimestamp } from 'shared/date';

import styles from './index.module.less';
import classNames from 'classnames';

interface CreateTimeProps {
  time: number;
  style?: CSSProperties;
  className?: string;
}

function CreateTime({ time, style }: CreateTimeProps): ReactElement {
  const _time = formatTimestamp(time);
  return (
    <div className={`${styles.create_time_container} ${classNames}`} style={style}>
      {_time}
    </div>
  );
}

export default CreateTime;
