import React, { ReactElement, useRef, useState, CSSProperties } from 'react';
import { useMount } from 'react-use';
import { Tooltip } from '@arco-design/web-react';

import styles from './index.module.less';

interface CreateTimeProps {
  text: string;
  style?: CSSProperties;
}

function ProjectName({ text, style }: CreateTimeProps): ReactElement {
  const eleRef = useRef<HTMLDivElement>();
  const [toolTipContent, setToolTipContent] = useState<string | undefined>();

  useMount(() => {
    // Check element overflow at next-tick
    setImmediate(() => {
      const { current } = eleRef;
      if (current) {
        if (current.scrollWidth > current.offsetWidth) {
          setToolTipContent(text);
        }
      }
    });
  });
  return (
    <Tooltip content={toolTipContent}>
      <div className={styles.project_name_container} ref={eleRef as any} style={style}>
        {text}
      </div>
    </Tooltip>
  );
}

export default ProjectName;
