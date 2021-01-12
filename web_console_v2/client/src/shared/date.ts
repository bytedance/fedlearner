import dayjs from 'dayjs';

export function formatTimestamp(input: number) {
  if (input.toString().length === 10) {
    return dayjs.unix(input).format('YYYY-MM-DD HH:mm:ss');
  }

  return dayjs(input).format('YYYY-MM-DD HH:mm:ss');
}
