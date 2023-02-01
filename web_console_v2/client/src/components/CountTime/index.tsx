import { noop } from 'lodash-es';
import React, { FC, useState, useEffect, useCallback } from 'react';
import { formatTimeCount } from 'shared/date';

export function formatSecound(input: number): string {
  return input.toString();
}

type Props = {
  /** Accurate to seconds */
  time: number;
  /** Stop count timer */
  isStatic?: boolean;
  /** Enable render props mode */
  isRenderPropsMode?: boolean;
  /** Reset time when changing isStatic value from false to true */
  isResetOnChange?: boolean;
  /** Is count down, otherwise, count up  */
  isCountDown?: boolean;
  /** Only show second  */
  isOnlyShowSecond?: boolean;
  /** When time less than or equal 0, call this function one time */
  onCountDownFinish?: () => void;
};
const CountTime: FC<Props> = ({
  time,
  isStatic = false,
  isRenderPropsMode = false,
  isResetOnChange = false,
  isCountDown = false,
  isOnlyShowSecond = false,
  onCountDownFinish,
  children,
}) => {
  const formatFn = useCallback(
    (inputTime: number) => {
      return isOnlyShowSecond ? formatSecound(inputTime) : formatTimeCount(inputTime);
    },
    [isOnlyShowSecond],
  );

  const [formatted, setFormatted] = useState(formatFn(time));
  const [noFormattedTime, setNoFormattedTime] = useState(time);

  useEffect(() => {
    if (isStatic) {
      if (isResetOnChange) {
        setFormatted(formatFn(time));
        setNoFormattedTime(time);
      }
      return noop;
    }

    if (isCountDown && Number(noFormattedTime) <= 0) {
      return noop;
    }
    const timer = setTimeout(() => {
      const tempTime = isCountDown ? noFormattedTime - 1 : noFormattedTime + 1;
      setFormatted(formatFn(tempTime));
      setNoFormattedTime(tempTime);
    }, 1000);

    return () => clearTimeout(timer);
  }, [time, isStatic, isResetOnChange, isCountDown, formatFn, noFormattedTime]);

  useEffect(() => {
    if (isCountDown && onCountDownFinish && Number(noFormattedTime) <= 0) {
      onCountDownFinish();
    }
  }, [noFormattedTime, isCountDown, onCountDownFinish]);

  if (isRenderPropsMode && typeof children === 'function') {
    return children(formatted, noFormattedTime);
  }

  return <span>{formatted}</span>;
};

export default CountTime;
