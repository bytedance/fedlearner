import styled from 'styled-components';
import { MixinSquare } from 'styles/mixins';

export const Container = styled.div`
  position: relative;
  /* TODO: remove the hard-coded 48px of chart header */
  height: ${(props: any) => `calc(100% - ${props.top || '0px'} - 48px)`};
  background-color: var(--gray1);

  /* react flow styles override */
  .react-flow__node {
    border-radius: 4px;
    font-size: 1em;
    text-align: initial;
    background-color: transparent;
    cursor: initial;

    &.selected {
      --selected-background: #f2f6ff;
      --selected-border-color: var(--primaryColor);
    }

    &.selectable {
      cursor: pointer;

      &:hover {
        filter: drop-shadow(0px 4px 10px #e0e0e0);
      }
    }
  }
  .react-flow__handle {
    width: 6px;
    height: 6px;
    opacity: 0;
  }
  .react-flow__edge {
    &-path {
      stroke: var(--gray4);
    }
  }
  .react-flow__controls {
    top: 20px;
    right: 20px;
    left: auto;
    bottom: auto;
    box-shadow: none;

    &-button {
      ${MixinSquare(27)}
      border-radius: 4px;
      border-bottom: none;
      box-shadow: 0 2px 10px -2px rgba(0, 0, 0, 0.2);
    }
  }
`;
