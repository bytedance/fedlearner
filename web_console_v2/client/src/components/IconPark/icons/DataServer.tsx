/* tslint:disable: max-line-length */
/* eslint-disable max-len */
import React from 'react';
import { ISvgIconProps, IconWrapper } from '../runtime';

export default IconWrapper(
  'data-server',
  false,
  (props: ISvgIconProps) => (
    <svg width={props.size} height={props.size} viewBox="0 0 24 24" fill="currentColor">
      <g
        stroke="none"
        strokeWidth="1"
        fill="none"
        fill-rule="evenodd"
        stroke-linecap="square"
        stroke-linejoin="round"
      >
        <g transform="translate(-106.000000, -111.000000)" stroke="currentColor" strokeWidth="2">
          <g transform="translate(107.000000, 112.000000)">
            <path d="M0,17 C0,18.65685 1.343145,20 3,20 L17,20 C18.65685,20 20,18.65685 20,17" />
            <path d="M0,17 C0,15.34315 1.343145,14 3,14 L17,14 C18.65685,14 20,15.34315 20,17" />
            <path d="M0,17 L0,3 C0,1.343145 1.343145,0 3,0 L17,0 C18.65685,0 20,1.343145 20,3 L20,17" />
            <line x1="3" y1="17" x2="3.5" y2="17" />
            <line x1="11" y1="17" x2="17" y2="17" />
          </g>
        </g>
      </g>
    </svg>
  ),
  (props: ISvgIconProps) => `
`,
);
