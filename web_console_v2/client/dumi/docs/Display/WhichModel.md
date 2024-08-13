# WhichModel

展示模型名称的组件，通过传入模型的 id，来显示对应的模型名称

> 注意 ⚠️: 因为 `<WhichModel/>` 内部引入了 `recoil` 相关的函数，所以 Demo 代码中用 `<RecoilRoot/>` 作为根组件，防止报错。

<API src="components/WhichModel/index.tsx" exports='["default"]'></API>

## 常规使用

如果找不到 id 对应的模型的话，会显示`-`

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import WhichModel from 'components/WhichModel';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <div>
          id 为 1 的模型名称（假设存在）名称为：
          <WhichModel id="1" />
        </div>
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

## formatter

格式化模型名称的函数

默认 `formatter` 的函数

```tsx | pure
function defaultFormatter(model: Model) {
  return model.name;
}
```

下面是自定义`formatter`的例子

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import WhichModel from 'components/WhichModel';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <div>
          id 为 1 的模型名称（假设存在）名称为：
          <WhichModel
            id="1"
            formatter={(model) => {
              return `__${model.name}__`;
            }}
          />
        </div>
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```
