import React, { FC, useEffect, useRef } from 'react';
import { QueryKey, useQuery } from 'react-query';
import styled from 'styled-components';
import { Refresh, Expand, Pause, CaretRight } from 'components/IconPark';
import { convertToUnit } from 'shared/helpers';
import { MixinFlexAlignCenter, MixinSquare } from 'styles/mixins';
import { useToggle } from 'react-use';
import { Tooltip } from 'antd';
import { noop } from 'lodash';

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
const ControlButton = styled.div`
  ${MixinFlexAlignCenter()}
  ${MixinSquare(30)}

  display: flex;
  background-color: #fff;
  border-radius: 4px;
  color: var(--textColor);
  cursor: pointer;
  box-shadow: 0 3px 10px -2px rgba(0, 0, 0, 0.7);
  transform-origin: 50%;

  &:hover {
    > .anticon {
      transform: scale(1.2);
    }
  }

  & + & {
    margin-top: 8px;
  }
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

  const logsQuery = useQuery(queryKey, logsFetcher, {
    refetchOnWindowFocus: true,
    retry: 2,
    refetchInterval,
    enabled: typeof enabled === 'boolean' ? enabled && !paused : !paused,
  });

  const logs = logsQuery.data?.data || [];

  const isEmpty = logs.length === 0;

  useEffect(() => {
    if (areaRef.current) {
      // Auto scroll to bottom if new logs coming
      areaRef.current.scrollTo({
        top: areaRef.current.scrollHeight,
        behavior: logsQuery.isInitialData ? 'smooth' : undefined,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logs]);

  return (
    <Container {...props}>
      <Pre ref={areaRef as any}>
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
          <Tooltip title={paused ? '自动刷新日志' : '停止自动刷新'}>
            {paused ? <CaretRight /> : <Pause />}
          </Tooltip>
        </ControlButton>
      </ControlsContainer>
    </Container>
  );
};

export default PrintLogs;
