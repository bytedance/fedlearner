/* istanbul ignore file */

import { keyframes } from 'styled-components';

export const Suspense = keyframes`
  0% {
    transform: translateY(0);
  }
  25% {
    transform: translateY(13%);
  }
  75% {
    transform: translateY(-13%);
  }
  100% {
    transform: translateY(0);
  }
`;

export const HighlightedWave = keyframes`
  0% {
    box-shadow: 0 0 0 2px var(--primaryColor);
  }
  33% {
    box-shadow: 0 0 0 2px var(--primaryColor), 0 0 0 5px var(--blue2);
  }
  66% {
    box-shadow: 0 0 0 2px var(--primaryColor), 0 0 0 10px transparent;
  }
  100% {
    box-shadow: 0 0 0 2px var(--primaryColor);
  }
`;
