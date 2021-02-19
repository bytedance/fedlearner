import React, { FC, useCallback, useEffect, useRef, useState } from 'react';
import { QueryKey, useQuery } from 'react-query';
import styled from 'styled-components';
import { Refresh, Expand, Pause, CaretRight, ArrowDown } from 'components/IconPark';
import { convertToUnit } from 'shared/helpers';
import { MixinFlexAlignCenter, MixinSquare } from 'styles/mixins';
import { ScrollDown } from 'styles/animations';
import { useToggle } from 'react-use';
import { Tooltip } from 'antd';
import { last, noop, debounce } from 'lodash';
import i18n from 'i18n';

const Container = styled.div`
  position: relative;
  width: ${(props: Props) => convertToUnit(props.width || '100%')};
  height: ${(props: Props) => convertToUnit(props.height || '100%')};
  background-color: #292238;
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
  text-shadow: 0 0 2px #001716, 0 0 3px #03edf975, 0 0 5px #03edf975, 0 0 8px #03edf975;
`;
const ControlsContainer = styled.div`
  position: absolute;
  top: 15px;
  right: 20px;
`;
const Button = styled.div`
  ${MixinFlexAlignCenter()}

  display: flex;
  background-color: #fff;
  border-radius: 4px;
  color: var(--textColor);
  cursor: pointer;
  box-shadow: 0 3px 10px -2px rgba(0, 0, 0, 0.7);
  transform-origin: 50%;

  &:hover {
    color: var(--primaryColor);

    > .anticon {
      transform: scale(1.1);
    }
  }
`;
const ControlButton = styled(Button)`
  ${MixinSquare(30)}

  & + & {
    margin-top: 8px;
  }
`;
const ScrollButton = styled(Button)`
  position: absolute;
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
  animation: ${ScrollDown} 1.2s linear infinite;
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
  const [paused, togglePaused] = useToggle(false);
  const [scroll2ButtVisible, setScroll2Butt] = useToggle(false);
  const [isFirstTimeResult, setFirstTime] = useState(true);
  const [lastestLog, setLastLog] = useState<string | undefined>('');

  const logsQuery = useQuery(queryKey, logsFetcher, {
    refetchOnWindowFocus: true,
    retry: 2,
    refetchInterval: refetchInterval || 5000,
    enabled: typeof enabled === 'boolean' ? enabled && !paused : !paused,
  });

  const logs = logsQuery.data?.data || [];
  const isEmpty = logs.length === 0;

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

  const debouncedScrollHandler = useCallback(debounce(onPreScroll, 200), [isAtButt, onPreScroll]);

  return (
    <Container {...props}>
      <Pre ref={areaRef as any} onScroll={debouncedScrollHandler}>
        {logsQuery.isLoading ? (
          <Refresh spin style={{ fontSize: '20px' }} />
        ) : isEmpty ? (
          'No logs at the moment'
        ) : (
          logsQuery.data?.data.join('\n')
        )}
      </Pre>
      <ControlsContainer>
        {fullscreenVisible && (
          <ControlButton onClick={onFullscreenClick || noop}>
            <Expand />
          </ControlButton>
        )}

        <ControlButton onClick={() => togglePaused()}>
          <Tooltip
            title={
              paused
                ? i18n.t('workflow.btn_auto_refresh_logs')
                : i18n.t('workflow.btn_pause_auto_refresh')
            }
          >
            {paused ? <CaretRight /> : <Pause />}
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

    return preElement.scrollHeight - (preElement.scrollTop + window.innerHeight) < 16;
  }

  function onPreScroll(event: any) {
    if (isAtButt(event.target)) {
      setScroll2Butt(false);
    }
  }
};

export default PrintLogs;
