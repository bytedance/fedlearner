# CheckboxWithPopconfirm

带有二次确认功能的 Checkbox 组件，基于[Arco Checkbox](xxx) 和 [Arco Popconfirm](xxx)封装

<API src="components/CheckboxWithPopconfirm/index.tsx"></API>

## 常规使用

```tsx
import React, { useState } from 'react';
import CheckboxWithPopconfirm from 'components/CheckboxWithPopconfirm';

export default () => {
  const [value, setValue] = useState(false);
  return (
    <CheckboxWithPopconfirm
      title="Are you confirm?"
      text="checkbox text"
      value={value}
      onChange={(val: any) => {
        console.log(val);
        setValue(val);
      }}
    />
  );
};
```
