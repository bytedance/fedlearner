/* istanbul ignore file */

import React from 'react';
import { Reply } from 'components/IconPark';
import styled from './elements.module.less';

export function AnchorIcon({ children, ...props }: any) {
  return <Reply className={styled.anchor_icon} />;
}

export function Details({ children, ...props }: any) {
  return (
    <div className={styled.details} {...props}>
      {children}
    </div>
  );
}

export function Summary({ children, ...props }: any) {
  return (
    <div className={styled.summary} {...props}>
      {children}
    </div>
  );
}

export function Container({ children, ...props }: any) {
  return (
    <div className={styled.container} {...props}>
      {children}
    </div>
  );
}

export function Name({ children, ...props }: any) {
  return (
    <strong className={styled.name} {...props}>
      {children}
    </strong>
  );
}

export function SearchBox({ children, ...props }: any) {
  return (
    <div className={styled.search_box} {...props}>
      {children}
    </div>
  );
}
