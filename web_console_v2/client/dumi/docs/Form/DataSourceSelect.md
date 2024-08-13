# DataSourceSelect

数据源下拉框，内部封装了获取数据源列表的网络请求

> 注意 ⚠️: 因为 `<DataSourceSelect/>` 内部引入了 `react-query` 相关的函数，所以 Demo 代码中用 `<QueryClientProvider/>` 作为根组件，防止报错。

# API

<API src="components/DataSourceSelect/index.tsx"></API>

其他与 [Arco Select](https://arco.design/react/components/select#api) 一样

## 常规用法

默认展示所有数据源

```jsx
import React, { useState } from 'react';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import { RecoilRoot } from 'recoil';

import DataSourceSelect from 'components/DataSourceSelect';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <DataSourceSelect
          style={{ width: 300 }}
          placeholder="dataset"
          allowClear
          showSearch
          onChange={(val) => {
            console.log(val);
          }}
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```
