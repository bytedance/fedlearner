import React, { FC, useState } from 'react';
import { TimePicker, Select } from '@arco-design/web-react';
import dayjs, { Dayjs } from 'dayjs';
import objectSupport from 'dayjs/plugin/objectSupport';

import styles from './index.module.less';

dayjs.extend(objectSupport);

const { Option } = Select;

export interface PickerValue {
  method: string;
  weekday?: number;
  time: Dayjs | null;
}

type Props = {
  value?: PickerValue;
  onChange?: (value: PickerValue) => void;
};

const CronTimePicker: FC<Props> = ({ value, onChange }) => {
  const [method, setMethod] = useState(value?.method!);
  const [weekday, setWeekday] = useState(value?.weekday || 0);
  const [time, setTime] = useState<Dayjs | null>(value?.time || null);

  return (
    <div className={styles.time_picker_container}>
      <Select
        onChange={(val) => {
          setMethod(val);
          onChange && onChange({ method: val, weekday, time });
        }}
        value={method}
      >
        <Option value="hour">每时</Option>
        <Option value="day">每天</Option>
        <Option value="week">每周</Option>
      </Select>
      <div />
      {method === 'week' && (
        <>
          <Select
            onChange={(val) => {
              setWeekday(val);
              onChange && onChange({ method, weekday: val, time });
            }}
            value={weekday}
          >
            <Option value={0}>星期天</Option>
            <Option value={1}>星期一</Option>
            <Option value={2}>星期二</Option>
            <Option value={3}>星期三</Option>
            <Option value={4}>星期四</Option>
            <Option value={5}>星期五</Option>
            <Option value={6}>星期六</Option>
          </Select>
          <div />
        </>
      )}

      <TimePicker
        value={time as any}
        onChange={(_, val: any) => {
          setTime(val);
          onChange && onChange({ method, weekday: val, time: val });
        }}
        format={method === 'hour' ? 'mm 分' : 'HH 时 : mm 分'}
        showNowBtn={false}
        placeholder={method === 'hour' ? '- 分' : '- 时 - 分'}
      />
    </div>
  );
};

/**
 * PickerValue in local format -> Cron in UTC format
 * @param value
 * @returns
 */
export function toCron(value: PickerValue) {
  const { method, weekday, time } = formatWithUtc(value, true);
  let cron = 'null';
  if (time) {
    if (method === 'week') {
      cron = `${time.minute()} ${time.hour()} * * ${weekday}`;
    } else if (method === 'day') {
      cron = `${time.minute()} ${time.hour()} * * *`;
    } else if (method === 'hour') {
      cron = `${time.minute()} * * * *`;
    }
  }
  return cron;
}

/**
 * Cron in UTC format -> PickerValue in local format
 * @param cron
 * @returns
 */
export function parseCron(cron: string) {
  const parsed: PickerValue = {
    method: 'day',
    time: null,
  };
  if (cron && cron !== 'null') {
    const cronArray = cron.split(' ');
    const cronLen = cronArray.length;
    if (cronArray[cronLen - 1] !== '*') {
      // This means that the time is based on the day of the week
      parsed.weekday = Number(cronArray[cronLen - 1]);
      parsed.method = 'week';
    }
    if (cronLen === 5) {
      if (cronArray[1] === '*') {
        parsed.method = 'hour';
        parsed.time = dayjs().set({
          minute: Number(cronArray[0]),
          second: 0,
        });
      } else {
        parsed.time = dayjs().set({
          hour: Number(cronArray[1]),
          minute: Number(cronArray[0]),
        });
      }
    }
  }
  return formatWithUtc(parsed, false);
}

export function formatWithUtc({ method, weekday, time }: PickerValue, isToUtc: boolean) {
  if (time) {
    let offsetHour = dayjs().utcOffset() / 60;
    !isToUtc && (offsetHour = 0 - offsetHour);
    const newHour = time.hour() - offsetHour;
    if (method === 'week' && weekday !== undefined) {
      let utcWeekday = weekday;
      if (newHour < 0) {
        utcWeekday -= 1;
      }
      if (newHour > 23) {
        utcWeekday += 1;
      }
      weekday = (utcWeekday + 7) % 7;
    }
    time = dayjs().set({ second: time.second(), minute: time.minute(), hour: (newHour + 24) % 24 });
  }
  return { method, weekday, time };
}

export default CronTimePicker;
