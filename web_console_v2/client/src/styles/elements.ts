/* istanbul ignore file */

import styled from 'styled-components';
import { MixinFlexAlignCenter, MixinSquare, MixinBaseFontInfo } from './mixins';

export const ControlButton = styled.div`
  ${MixinFlexAlignCenter()}
  ${MixinSquare(30)}

  display: flex;
  background-color: #fff;
  border-radius: 4px;
  color: var(--textColor);
  cursor: pointer;
  box-shadow: 0 3px 10px -2px rgba(0, 0, 0, 0.2);
  transform-origin: 50%;

  &:hover {
    color: var(--primaryColor);

    > .anticon {
      transform: scale(1.1);
    }
  }

  & + & {
    margin-top: 8px;
  }
`;

export type LabelProps = {
  /**
   * margin-right
   * @default 0
   */
  marginRight?: number;
  /**
   * when isBlock = true, display: block, otherwise display: inline-block
   * @default false
   */
  isBlock?: boolean;
  /**
   * font-size
   * @default 12
   */
  fontSize?: number;
  /**
   * color
   * @default var(--textColor)
   */
  fontColor?: string;
  /**
   * font-weight
   * @default 400
   */
  fontWeight?: number;
};

export const Label = styled.span<LabelProps>`
  ${(props) => {
    const { fontSize = 12, fontColor = 'var(--textColor)', fontWeight = 400 } = props;
    return MixinBaseFontInfo(fontSize, fontColor, fontWeight);
  }}
  display: ${(props) => (props.isBlock ? 'block' : 'inline-block')};
  margin-right: ${(props) => props.marginRight || 0}px;
`;

export const LabelStrong = styled(Label).attrs((props: any) => ({
  fontSize: props.fontSize || 12,
  fontColor: props.fontColor || 'var(--textColorStrong)',
  fontWeight: props.fontWeight || 500,
}))``;

export const LabelTint = styled(Label).attrs((props: any) => ({
  fontSize: props.fontSize || 12,
  fontColor: props.fontColor || 'var(--textColorSecondary)',
  fontWeight: props.fontWeight || 400,
}))``;

export const LabelForm = styled(Label).attrs((props: any) => ({
  fontSize: props.fontSize || 13,
  fontColor: props.fontColor || 'rgba(0, 0, 0, 0.85)',
  fontWeight: props.fontWeight || 400,
}))``;
