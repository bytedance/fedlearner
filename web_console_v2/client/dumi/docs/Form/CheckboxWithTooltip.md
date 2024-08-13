# CheckboxWithTooltip

带有 Tooptip 提示功能的 Checkbox 组件，基于[Arco Checkbox](xxx) 和 [Arco Tooltip](xxx)封装

<API src="components/CheckboxWithTooltip/index.tsx"></API>

## 常规使用

```tsx
import React, { useState } from 'react';
import CheckboxWithTooltip from 'components/CheckboxWithTooltip';

export default () => {
  const [value, setValue] = useState(false);
  return (
    <CheckboxWithTooltip
      tip="I am tooltip"
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
