# DatasetSelect

数据集下拉框，内部封装了获取数据集列表的网络请求，并自定义了 children 渲染布局

> 注意 ⚠️: 因为 `<DatasetSelect/>` 内部引入了 `react-query` 相关的函数，所以 Demo 代码中用 `<QueryClientProvider/>` 作为根组件，防止报错。

<API src="components/DatasetSelect/index.tsx" exports='["default"]' ></API>

> 注意 ⚠️: value 和 onChange 的值是 `Dataset` 类型，不是 any(dumi 不支持外部 type，所以显示成 any？)，具体字段请查看 `import { Dataset } from 'typings/dataset'`

<API src="components/DatasetSelect/index.tsx" exports='["DatasetPathSelect"]' ></API>

## 常规用法

默认展示所有数据集

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import DatasetSelect from 'components/DatasetSelect';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <DatasetSelect
          style={{ width: 300 }}
          placeholder="dataset"
          onChange={(val) => {
            console.log(val);
          }}
          allowClear
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

## Kind

根据 kind 来过滤数据集

```
0 - training dataset
1 - test dataset
2 - predict dataset
```

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import DatasetSelect from 'components/DatasetSelect';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <div>训练数据集</div>
        <DatasetSelect
          style={{ width: 300 }}
          placeholder="dataset"
          onChange={(val) => {
            console.log(val);
          }}
          allowClear
          kind={0}
        />
        <div>评估数据集</div>
        <DatasetSelect
          style={{ width: 300 }}
          placeholder="dataset"
          onChange={(val) => {
            console.log(val);
          }}
          allowClear
          kind={1}
        />
        <div>预测数据集</div>
        <DatasetSelect
          style={{ width: 300 }}
          placeholder="dataset"
          onChange={(val) => {
            console.log(val);
          }}
          allowClear
          kind={2}
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

## 无数据

无数据的情况下，会显示文本`暂无数据集 去创建`，点击`去创建`，会跳转到数据集列表页面

## 子组件

### DatasetPathSelect

特殊处理 value 和 onChange，提取 dataset.path 字符串

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import { DatasetPathSelect } from 'components/DatasetSelect';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <DatasetPathSelect
          style={{ width: 300 }}
          placeholder="dataset path"
          onChange={(val) => {
            console.log(val);
          }}
          allowClear
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```
