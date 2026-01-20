# WhichParticipantDataset

展示合作伙伴数据集名称的组件，通过传入合作数据集的 uuid，来显示对应的数据集名称

> 注意 ⚠️: 因为 `<WhichParticipantDataset/>` 内部引入了 `recoil` 相关的函数，所以 Demo 代码中用 `<RecoilRoot/>` 作为根组件，防止报错。

内部封装了获取所有数据集列表的接口的逻辑，可以从 Cache 中，根据 uuid 找到对应的数据集

<API src="components/WhichParticipantDataset/index.tsx" exports='["default"]'></API>

## 常规使用

如果找不到 uuid 对应的合作伙伴数据集的话，会显示`-`

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import WhichParticipantDataset from 'components/WhichParticipantDataset';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <div>
          uuid 为 u26af7e549f30473382a 的数据集（假设存在）名称为：
          <WhichParticipantDataset uuid="u26af7e549f30473382a" />
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

import WhichParticipantDataset from 'components/WhichParticipantDataset';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <WhichParticipantDataset uuid={2} loading={true} />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```
