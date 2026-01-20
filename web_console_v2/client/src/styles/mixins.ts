import { convertToUnit } from 'shared/helpers';
import defaultTheme from './theme';

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
export function MixinEllipsis(maxWidth?: any, unit?: string) {
  return `
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: ${convertToUnit(maxWidth ?? 'auto', unit)};
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

export function MixinWritableShape() {
  return `
    width: 13px;
    height: 11px;
    background-color: var(--primaryColor);
    clip-path: polygon(50% 0, 100% 100%, 0 100%, 50% 0);
    transform: translateY(-0.5px);
  `;
}

export function MixinReadableShape() {
  return `
    ${MixinSquare(11)};

    background-color: var(--successColor);
  `;
}
export function MixinPrivateShape() {
  return `
    ${MixinCircle(12)};

    background-color: var(--warningColor);
  `;
}

export function MixinBaseFontInfo(
  fontSize: number = 12,
  color: any = 'var(--textColor)',
  fontWeight: any = 400,
) {
  return `
    font-size: ${fontSize}px;
    color: ${color};
    font-weight: ${fontWeight};
  `;
}
