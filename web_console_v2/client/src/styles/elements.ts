import styled from 'styled-components';
import { MixinFlexAlignCenter, MixinSquare } from './mixins';

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
