import React, { FC, useContext, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { useToggle } from 'react-use';
import { JobExecutionDetailsContext } from '../../JobExecutionDetailsDrawer';
import { ControlButton } from 'styles/elements';
import { ControlsContainer } from '../elements';
import { Pen, ShareInternal } from 'components/IconPark';

const EmbeddedFrame = styled.iframe`
  width: 200%;
  height: 600px;
  border: none;
  flex-shrink: 0;
  transform: scale(0.5);
  transform-origin: 0 0;
`;

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
      <EmbeddedFrame
        role="kibana-iframe"
        ref={(el) => (iframeRef.current = el)}
        src={src ? `${src}&embed=true` : undefined}
        onLoad={onLoaded}
      />
      {isFill && (
        <ControlsContainer>
          <ControlButton onClick={onEditParams}>
            <Pen />
          </ControlButton>
          <ControlButton onClick={() => onOpenNewWindow(src)}>
            <ShareInternal />
          </ControlButton>
        </ControlsContainer>
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
