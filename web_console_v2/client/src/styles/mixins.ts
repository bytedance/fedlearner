import { convertToUnit } from 'shared/helpers'
import defaultTheme from './_theme'

export function Square(size: any) {
  const converted = convertToUnit(size)
  return `
    width: ${converted};
    height: ${converted};
  `
}

export function FlexAlignCenter() {
  return `
    justify-content: center;
    align-items: center;
  `
}

export function commonTransition(props: string | string[] | undefined) {
  if (!props) return `transition: 0.2s ${defaultTheme.commonTiming}`

  const arr = []

  if (typeof props === 'string') {
    arr.push(props)
  } else {
    arr.push(...props)
  }

  return `
    transition: ${arr.map((i) => `${i} 0.2s ${defaultTheme.commonTiming}`).join(',')}
  `
}
