# WhichProject

展示工作区名称的组件，通过传入工作区的 id，来显示对应的工作区名称

> 注意 ⚠️: 因为 `<WhichProject/>` 内部引入了 `recoil` 相关的函数，所以 Demo 代码中用 `<RecoilRoot/>` 作为根组件，防止报错。

内部封装了获取所有工作区列表的接口的逻辑，可以从 Cache 中，根据 id 找到对应的工作区

<API src="components/WhichProject/index.tsx"></API>

## 常规使用

如果找不到 id 对应的工作区的话，会显示`--`

```jsx
import React, { useState } from 'react';
import { RecoilRoot } from 'recoil';

import WhichProject from 'components/WhichProject';

export default () => {
  return (
    <RecoilRoot>
      <div>
        id 为 1 的工作区（假设存在）名称为：
        <WhichProject id={1} />
      </div>
      <div>
        id 为 110 的工作区（假设不存在）名称为：
        <WhichProject id={110} />
      </div>
    </RecoilRoot>
  );
};
```

## loading

强制显示 loading

```jsx
import React, { useState } from 'react';
import { RecoilRoot } from 'recoil';

import WhichProject from 'components/WhichProject';

export default () => {
  return (
    <RecoilRoot>
      <WhichProject id={1} loading={true} />
    </RecoilRoot>
  );
};
```
