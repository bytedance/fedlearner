import { convertToUnit } from 'shared/helpers';
import defaultTheme from './_theme';

/* istanbul ignore next */
export function MixinFontClarity() {
  return `
    font-family: 'ClarityMono', sans-serif;
  `;
}

export function MixinSquare(size: any) {
  const converted = convertToUnit(size);
  return `
    width: ${converted};
    height: ${converted};
  `;
}

export function MixinCircle(diameter: any) {
  return `
    ${MixinSquare(diameter)}
    border-radius: 50%;
  `;
}

/* istanbul ignore next */
export function MixinFlexAlignCenter() {
  return `
    justify-content: center;
    align-items: center;
  `;
}

/* istanbul ignore next */
export function MixinEllipsis() {
  return `
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  `;
}

export function MixinCommonTransition(
  props?: string | string[] | undefined,
  duration: number = 0.4,
) {
  if (!props) return `transition: ${duration}s ${defaultTheme.commonTiming};`;

  const arr: string[] = [];

  if (typeof props === 'string') {
    arr.push(props);
  } else {
    arr.push(...props);
  }

  return `
    transition: ${arr.map((i) => `${i} ${duration}s ${defaultTheme.commonTiming}`).join(',')};
  `;
}
