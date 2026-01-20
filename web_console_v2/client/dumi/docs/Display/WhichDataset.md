# WhichDataset

展示数据集名称的组件，通过传入数据集的 id，来显示对应的数据集名称

数据集有 4 种,`原始数据集`、`结果数据集`、`合作伙伴数据集`、`求交数据集`

其中合作伙伴数据集只能通过[WhichParticipantDataset](/display/which-participant-dataset)来获取

其中求交数据集只能通过[WhichDataset.IntersectionDataset](#intersectiondataset)来获取

> 注意 ⚠️: 因为 `<WhichDataset/>` 内部引入了 `recoil` 相关的函数，所以 Demo 代码中用 `<RecoilRoot/>` 作为根组件，防止报错。

内部封装了获取所有数据集列表的接口的逻辑，可以从 Cache 中，根据 id 找到对应的数据集

<API src="components/WhichDataset/index.tsx" exports='["default"]'></API>

## 常规使用

如果找不到 id 对应的数据集（原始+结果）的话，会显示`-`

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import WhichDataset from 'components/WhichDataset';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <div>
          id 为 1 的数据集（假设存在）名称为：
          <WhichDataset id={1} />
        </div>
        <div>
          id 为 110 的数据集（假设不存在）名称为：
          <WhichDataset id={110} />
        </div>
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

## loading

强制显示 loading

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import WhichDataset from 'components/WhichDataset';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <WhichDataset id={2} loading={true} />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

## 子组件

### UUID

根据 UUID 来寻找数据集（原始+结果）

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import WhichDataset from 'components/WhichDataset';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <div>
          uuid 为 8 的数据集（假设不存在）名称为：
          <WhichDataset.UUID id={8} />
        </div>
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

### IntersectionDataset

求交数据集

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import WhichDataset from 'components/WhichDataset';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <div>
          id 为 1 的求交数据集（假设存在）名称为：
          <WhichDataset.IntersectionDataset id={1} />
        </div>
        <div>
          id 为 110 的求交数据集（假设不存在）名称为：
          <WhichDataset.IntersectionDataset id={110} />
        </div>
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```
