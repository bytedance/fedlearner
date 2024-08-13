import React, { FC, useContext, useEffect, useRef } from 'react';
import styled from './EmbeddedChart.module.less';
import { useToggle } from 'react-use';
import { JobExecutionDetailsContext } from '../../JobExecutionDetailsDrawer';
import { ControlButton } from 'styles/elements';
import { IconPen, IconShareInternal } from '@arco-design/web-react/icon';

type Props = { src?: string; isFill?: boolean; onEditParams: any; onOpenNewWindow: any };

const KibanaEmbeddedChart: FC<Props> = ({ src, isFill, onEditParams, onOpenNewWindow }) => {
  const iframeRef = useRef<HTMLIFrameElement | null>();
  const [, toggleLoaded] = useToggle(false);

  const context = useContext(JobExecutionDetailsContext);

  useEffect(() => {
    toggleLoaded(false);
  }, [context.job?.id, toggleLoaded]);

  return (
    <div style={{ width: '100%' }}>
      <iframe
        title="kibana-iframe"
        className={styled.embedded_frame}
        // eslint-disable-next-line jsx-a11y/aria-role
        role="kibana-iframe"
        ref={(el) => (iframeRef.current = el)}
        src={src ? `${src}&embed=true` : undefined}
        onLoad={onLoaded}
      />
      {isFill && (
        <div className={styled.controls_container}>
          <ControlButton onClick={onEditParams}>
            <IconPen />
          </ControlButton>
          <ControlButton onClick={() => onOpenNewWindow(src)}>
            <IconShareInternal />
          </ControlButton>
        </div>
      )}
    </div>
  );

  function onLoaded() {
    if (src) {
      toggleLoaded(true);
    }
  }
};

export default KibanaEmbeddedChart;
