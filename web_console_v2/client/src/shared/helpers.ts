/**
 * @param time time in ms
 */
export function sleep(time: number): Promise<null> {
  return new Promise((resolve) => {
    setTimeout(resolve, time)
  })
}
