import { convertToUnit } from 'shared/helpers'
import defaultTheme from './_theme'

export function MixinSquare(size: any) {
  const converted = convertToUnit(size)
  return `
    width: ${converted};
    height: ${converted};
  `
}

export function MixinCircle(diameter: any) {
  return `
    ${MixinSquare(diameter)}
    border-radius: 50%;
  `
}

export function MixinFlexAlignCenter() {
  return `
    justify-content: center;
    align-items: center;
  `
}

export function MixinEllipsis() {
  return `
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  `
}

export function MixinCommonTransition(props?: string | string[] | undefined) {
  if (!props) return `transition: 0.4s ${defaultTheme.commonTiming};`

  const arr: string[] = []

  if (typeof props === 'string') {
    arr.push(props)
  } else {
    arr.push(...props)
  }

  return `
    transition: ${arr.map((i) => `${i} 0.4s ${defaultTheme.commonTiming}`).join(',')};
  `
}
