/* istanbul ignore file */

import React, { FC, useCallback, useEffect, useRef, useState } from 'react';
import { QueryKey, useQuery } from 'react-query';
import styled from 'styled-components';
import { Refresh, Expand, Pause, CaretRight, ArrowDown } from 'components/IconPark';
import { convertToUnit } from 'shared/helpers';
import { Suspense } from 'styles/animations';
import { useToggle } from 'react-use';
import { Tooltip, Message } from '@arco-design/web-react';
import { last, debounce } from 'lodash-es';
import i18n from 'i18n';
import { ControlButton } from 'styles/elements';
import { Download } from 'components/IconPark';
import { saveBlob } from 'shared/helpers';

const Container = styled.div`
  position: relative;
  width: ${(props: Props) => convertToUnit(props.width || '100%')};
  height: ${(props: Props) => convertToUnit(props.height || '100%')};
  background-color: #292238;
  border-radius: 4px;
`;
const Pre = styled.pre`
  width: 100%;
  height: 100%;
  padding: 15px;
  white-space: pre-wrap;
  color: #fefefe;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  transform: translate3d(0, 0, 0);
`;
const ControlsContainer = styled.div`
  position: absolute;
  top: 15px;
  right: 20px;
`;
const ScrollButton = styled(ControlButton)`
  position: absolute;
  width: auto;
  height: auto;
  bottom: 10px;
  left: 50%;
  padding: 5px 15px 5px 10px;
  line-height: 20px;
  font-size: 12px;
  transform: translateX(-50%);

  > .anticon {
    margin-right: 5px;
  }
`;
const AnimatedArrowDown = styled(ArrowDown)`
  animation: ${Suspense} 1.2s linear infinite;
`;

type Props = {
  width?: any;
  height?: any;
  refetchInterval?: number;
  enabled?: boolean;
  queryKey: QueryKey;
  logsFetcher(...args: any[]): Promise<{ data: string[] }>;
  onFullscreenClick?: any;
  fullscreenVisible?: boolean;
};

const PrintLogs: FC<Props> = (props) => {
  const {
    queryKey,
    logsFetcher,
    refetchInterval,
    enabled,
    onFullscreenClick,
    fullscreenVisible,
  } = props;
  const areaRef = useRef<HTMLPreElement>();
  const containerRef = useRef<HTMLDivElement>();
  const [paused, togglePaused] = useToggle(false);
  const [scroll2ButtVisible, setScroll2Butt] = useToggle(false);
  const [isFirstTimeResult, setFirstTime] = useState(true);
  const [lastestLog, setLastLog] = useState<string | undefined>('');

  const logsQuery = useQuery(queryKey, () => logsFetcher(), {
    refetchOnWindowFocus: true,
    retry: 2,
    refetchInterval: refetchInterval || 5000,
    enabled: typeof enabled === 'boolean' ? enabled && !paused : !paused,
  });

  const logs = logsQuery.data?.data || [];
  const isEmpty = logs.length === 0;

  useEffect(() => {
    setFirstTime(true);
  }, [logsFetcher]);

  useEffect(() => {
    const preElement = areaRef.current;
    const newLastestLog = last(logs);

    if (preElement && logs.length) {
      if (isFirstTimeResult) {
        // Auto scroll to bottom if logs been fetched 1st time
        scrollToButt();
        setFirstTime(false);
      } else {
        /**
         * When user scroll to higher position
         * and there comes new logs at the tail
         * show user the scroll-to-bottom button
         */
        const notAtButt = !isAtButt(preElement);

        if (lastestLog !== newLastestLog && notAtButt) {
          setScroll2Butt(true);
        }
      }
    }
    setLastLog(newLastestLog);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logs, isFirstTimeResult, lastestLog]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const debouncedScrollHandler = useCallback(debounce(onPreScroll, 200), [isAtButt, onPreScroll]);

  let logsContent: string = '';

  if (logsQuery.isError) {
    logsContent = (logsQuery.error as any).message;
  } else if (isEmpty) {
    logsContent = 'No logs at the moment';
  } else if (logsQuery.data) {
    logsContent = Array.isArray(logsQuery.data.data)
      ? logsQuery.data.data?.join('\n')
      : logsQuery.data.toString();
  }

  return (
    <Container {...props} ref={containerRef as any}>
      <Pre ref={areaRef as any} onScroll={debouncedScrollHandler}>
        {logsQuery.isLoading ? <Refresh spin style={{ fontSize: '20px' }} /> : logsContent}
      </Pre>
      <ControlsContainer>
        {fullscreenVisible && Boolean(onFullscreenClick) && (
          <ControlButton onClick={onFullscreenClick}>
            <Tooltip content={i18n.t('workflow.btn_full_screen')} position="left">
              <Expand />
            </Tooltip>
          </ControlButton>
        )}

        <ControlButton onClick={() => togglePaused()}>
          <Tooltip
            position="left"
            content={
              paused
                ? i18n.t('workflow.btn_auto_refresh_logs')
                : i18n.t('workflow.btn_pause_auto_refresh')
            }
          >
            {paused ? <CaretRight /> : <Pause />}
          </Tooltip>
        </ControlButton>
        <ControlButton onClick={() => onDownload()}>
          <Tooltip position="left" content={i18n.t('workflow.action_download_log')}>
            <Download />
          </Tooltip>
        </ControlButton>
      </ControlsContainer>

      {scroll2ButtVisible && (
        <ScrollButton onClick={scrollToButt}>
          <AnimatedArrowDown />
          {i18n.t('workflow.btn_has_new_logs')}
        </ScrollButton>
      )}
    </Container>
  );

  function scrollToButt() {
    if (areaRef.current) {
      areaRef.current.scrollTo({
        top: areaRef.current.scrollHeight,
        behavior: 'smooth',
      });

      setScroll2Butt(false);
    }
  }

  function isAtButt(pre?: HTMLPreElement) {
    const preElement = pre || areaRef.current;
    if (!preElement) return true;

    return (
      preElement.scrollHeight - (preElement.scrollTop + containerRef.current!.offsetHeight) < 16
    );
  }

  function onPreScroll(event: any) {
    if (isAtButt(event.target)) {
      setScroll2Butt(false);
    }
  }
  async function onDownload() {
    try {
      const data = await logsFetcher(5000);
      if (data.data) {
        const blob = new Blob([JSON.stringify(data.data, null, 2)], {
          type: 'application/json',
        });
        saveBlob(blob, `log.json`);
      }
    } catch (error) {
      Message.error(error.message);
    }
  }
};

export default PrintLogs;
