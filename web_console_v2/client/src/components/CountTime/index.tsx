import { noop } from 'lodash';
import React, { FC, useState, useEffect } from 'react';
import { fomatTimeCount } from 'shared/date';

const CountTime: FC<{ time: number; isStatic: boolean }> = ({ time, isStatic }) => {
  let [formatted, setFormatted] = useState(fomatTimeCount(time));

  useEffect(() => {
    if (isStatic) return noop;

    const timer = setInterval(() => {
      setFormatted(fomatTimeCount(time++));
    }, 1000);

    return () => clearInterval(timer);
  }, [time, isStatic]);

  return <span>{formatted}</span>;
};

export default CountTime;
