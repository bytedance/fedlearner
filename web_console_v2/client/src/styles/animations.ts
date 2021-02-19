import { keyframes } from 'styled-components';

export const ScrollDown = keyframes`
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
