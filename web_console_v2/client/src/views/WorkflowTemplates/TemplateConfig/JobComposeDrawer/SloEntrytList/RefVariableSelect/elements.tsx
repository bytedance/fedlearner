import React from 'react';
import styled from './elements.module.less';

export function NoAvailable({ children, ...props }: any) {
  return (
    <div className={styled.no_available} {...props}>
      {children}
    </div>
  );
}

export function OptionLabel({ children, ...props }: any) {
  return (
    <span className={styled.option_label} {...props}>
      {children}
    </span>
  );
}
