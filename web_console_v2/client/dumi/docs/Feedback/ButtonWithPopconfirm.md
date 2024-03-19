# ButtonWithPopconfirm

带有二次确认功能(气泡框)的 Button 组件，基于[Arco Button](xxx) 和 [Arco Popconfirm](xxx) 封装

<API src="components/ButtonWithPopconfirm/index.tsx"></API>

## 常规使用

```tsx
import React from 'react';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';

export default () => (
  <>
    <ButtonWithPopconfirm
      buttonText="Button"
      onConfirm={() => {
        console.log('confirm');
      }}
      onCancel={() => {
        console.log('cancel');
      }}
    />
  </>
);
```
