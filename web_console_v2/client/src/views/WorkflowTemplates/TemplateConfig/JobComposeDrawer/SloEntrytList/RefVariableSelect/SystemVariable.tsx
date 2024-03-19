import React, { FC, useState } from 'react';
import { Input } from '@arco-design/web-react';
import { RefModelSharedProps } from './types';

const PREFIX = 'system.variables';

const SystemVariable: FC<RefModelSharedProps> = ({ isCheck, value, onChange }) => {
  const varName = _parse(value);
  const [localVarname, setLocalVar] = useState(varName);

  return (
    <Input
      disabled={isCheck}
      value={localVarname}
      addBefore={`${PREFIX}.`}
      onChange={onInputChange}
      placeholder={'输入系统变量名'}
    />
  );

  function onInputChange(value: string, e: any) {
    setLocalVar(value);
    onChange && onChange(_compose(value));
  }
};

function _compose(val: string) {
  if (!val) return '';
  return `${PREFIX}.${val}`;
}
function _parse(reference: string | undefined): string {
  if (!reference) return '';
  const fragments = reference.split('.');
  if (fragments.length !== 3) {
    return '';
  }
  const [, , varName] = fragments;
  return varName;
}

export default SystemVariable;
