import { isNil } from 'lodash'

/**
 * @param time time in ms
 */
export function sleep(time: number): Promise<null> {
  return new Promise((resolve) => {
    setTimeout(resolve, time)
  })
}

/**
 * Convert value to css acceptable stuffs
 * @param val e.g. 10, '10%', '1.2em'
 * @param unit e.g. px, %, em...
 */
export function convertToUnit(val: any, unit = 'px'): string {
  if (isNil(val) || val === '') {
    return '0'
  } else if (isNaN(val)) {
    return String(val)
  } else {
    return `${Number(val)}${unit}`
  }
}

/**
 * Resolve promise inline
 */
export async function to<T, E = Error>(promise: Promise<T>): Promise<[T, E]> {
  try {
    const ret = await promise
    return [ret, (null as unknown) as E]
  } catch (e) {
    return [(null as unknown) as T, e]
  }
}
