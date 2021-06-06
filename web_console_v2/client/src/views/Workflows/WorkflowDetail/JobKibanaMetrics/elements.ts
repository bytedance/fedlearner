import styled from 'styled-components';
import { MixinCommonTransition } from 'styles/mixins';

export const ChartContainer = styled.div`
  ${MixinCommonTransition('height')};

  position: relative;
  display: flex;
  align-items: center;
  flex-direction: column;
  width: 100%;
  height: 300px;
  overflow: hidden;
  background-color: var(--backgroundColor);

  & + & {
    margin-top: 15px;
  }

  &[data-is-fill='true'] {
    > [role='kibana-iframe'] {
      width: 100%;
      height: 100%;
      transform: none;
    }
  }
`;
export const NotLoadedPlaceholder = styled.div`
  position: absolute;
  max-width: 50%;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  font-size: 12px;
  color: var(--textColorSecondary);
  text-align: center;
`;
export const ControlsContainer = styled.div`
  position: absolute;
  z-index: 2;
  right: 10px;
  bottom: 20px;
`;
