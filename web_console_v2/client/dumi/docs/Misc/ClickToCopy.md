# ClickToCopy

Copy 拷贝文本的组件

除了组件的形式，也可以使用核心 API `copyToClipboard`

```js
import { copyToClipboard } from 'shared/helpers';

const isOK = copyToClipboard(text);

if (isOK) {
  message.success('Copied success!');
} else {
  message.error('Copied fail!');
}
```

<API src="components/ClickToCopy/index.tsx"></API>

## 常规使用

目前需要手动从 props 传入所需要拷贝的文本，注意容器 width 宽度，它会影响最终的点击范围

```jsx
import React from 'react';
import ClickToCopy from 'components/ClickToCopy';

export default () => (
  <>
    <div style={{ display: 'inline-block' }}>
      <ClickToCopy text="text">Click me to Copy</ClickToCopy>
    </div>
  </>
);
```

## Tip

`successTip` 为 copy 拷贝成功的提示文案

`failTip` 为 copy 拷贝失败的提示文案

```jsx
import React from 'react';
import ClickToCopy from 'components/ClickToCopy';

export default () => (
  <>
    <ClickToCopy text="text" successTip="Copied success!" failTip="Copied fail!">
      Click me to Copy
    </ClickToCopy>
  </>
);
```
