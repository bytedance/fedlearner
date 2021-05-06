import React, { FC, useContext, useEffect, useRef } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { useToggle } from 'react-use';
import { JobExecutionDetailsContext } from '../JobExecutionDetailsDrawer';
import { MixinCommonTransition } from 'styles/mixins';
import { ControlButton } from 'styles/elements';
import { Pen, ShareInternal } from 'components/IconPark';

const Container = styled.div`
  ${MixinCommonTransition('height')};

  position: relative;
  display: flex;
  width: 100%;
  height: 300px;
  overflow: hidden;
  background-color: var(--backgroundColor);

  & + & {
    margin-top: 15px;
  }

  &[data-is-fill='true'] {
    > .kibana-iframe {
      width: 100%;
      height: 100%;
      transform: none;
    }
  }
`;
const EmbeddedFrame = styled.iframe`
  width: 200%;
  height: 600px;
  border: none;
  flex-shrink: 0;

  transform: scale(0.5);
  transform-origin: 0 0;
`;
const NotLoadedPlaceholder = styled.div`
  position: absolute;
  max-width: 50%;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  color: var(--textColorSecondary);
  text-align: center;
`;

const ControlsContainer = styled.div`
  position: absolute;
  z-index: 2;
  right: 10px;
  bottom: 20px;
`;

type Props = { src: string; fill?: boolean; onEditParams: any; onOpenNewWindow: any };

const KibanaEmbeddedChart: FC<Props> = ({ src, fill, onEditParams, onOpenNewWindow }) => {
  const { t } = useTranslation();
  const iframeRef = useRef<HTMLIFrameElement | null>();
  const [loaded, toggleLoaded] = useToggle(false);

  const context = useContext(JobExecutionDetailsContext);

  useEffect(() => {
    toggleLoaded(false);
  }, [context.job?.id, toggleLoaded]);

  return (
    <Container data-is-fill={fill}>
      {!loaded && (
        <NotLoadedPlaceholder>{t('workflow.placeholder_fill_kibana_form')}</NotLoadedPlaceholder>
      )}
      <EmbeddedFrame
        className="kibana-iframe"
        ref={(el) => (iframeRef.current = el)}
        src={src ? `${src}&embed=true` : undefined}
        onLoad={onLoaded}
      />
      {fill && (
        <ControlsContainer>
          <ControlButton onClick={onEditParams}>
            <Pen />
          </ControlButton>
          <ControlButton onClick={() => onOpenNewWindow(src)}>
            <ShareInternal />
          </ControlButton>
        </ControlsContainer>
      )}
    </Container>
  );

  function onLoaded() {
    if (src) {
      toggleLoaded(true);
    }
  }
};

export default KibanaEmbeddedChart;
