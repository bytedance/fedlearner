/* istanbul ignore file */

import React, { FC } from 'react';
import { Checkbox, Tooltip } from '@arco-design/web-react';

import { CheckboxProps } from '@arco-design/web-react/es/Checkbox';

type Props = {
  /** Tooltip title */
  tip?: string;
  /** Checkbox text */
  text?: string;
  /** Checkbox value */
  value?: boolean;
  onChange?: (val: boolean) => void;
} & CheckboxProps;
const CheckboxWithTooltip: FC<Props> = ({ value, onChange, tip, text, ...props }) => {
  return (
    <>
      <Tooltip content={tip}>
        <Checkbox
          onChange={(checked) => {
            onChange?.(checked);
          }}
          checked={value}
          {...props}
        >
          {text}
        </Checkbox>
      </Tooltip>
    </>
  );
};

export default CheckboxWithTooltip;
