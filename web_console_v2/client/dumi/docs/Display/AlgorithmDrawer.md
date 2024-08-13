# AlgorithmDrawer

基于 [Arco Drawer](https://arco.design/react/components/modal#api) 封装，展示某个算法版本具体信息的 Drawer 组件

> 注意 ⚠️: 因为组件内部引入了 `react-query` 相关的函数，所以 Demo 代码中用 `<QueryClientProvider/>` 作为根组件，防止报错。

<API src="components/AlgorithmDrawer/index.tsx" exports='["default"]'></API>

```tsx | pure
type AlgorithmParameter = {
  name: string;
  value: string;
  required: boolean;
  display_name: string;
  comment: string;
  value_type: ValueType;
};
```

## 常规使用

需要传递算法项目 algorithmProjectId 和算法版本 algorithmId 2 个 ID，组件会内部进行异步请求获取数据

```tsx
import React, { useState } from 'react';
import { RecoilRoot } from 'recoil';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import AlgorithmDrawer from 'components/AlgorithmDrawer';

export default () => {
  const [visible, setVisible] = useState(false);

  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <button
          onClick={() => {
            setVisible(true);
          }}
        >
          Click me show AlgorithmDrawer
        </button>
        <AlgorithmDrawer
          visible={visible}
          algorithmProjectId={3}
          algorithmId={3}
          onCancel={() => {
            setVisible(false);
          }}
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

## parameterVariables

如果需要显示额外的超参数的话，可以通过 parameterVariables 这个 props 来实现

如果设置`isAppendParameterVariables = true`,他会在原来的超参数数组上，额外增加你所传递的超参数

如果设置`isAppendParameterVariables = false`,会只显示 parameterVariables  中的超参数

```tsx
import React, { useState } from 'react';
import { RecoilRoot } from 'recoil';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import AlgorithmDrawer from 'components/AlgorithmDrawer';

export default () => {
  const [visible, setVisible] = useState(false);

  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <button
          onClick={() => {
            setVisible(true);
          }}
        >
          Click me show AlgorithmDrawer
        </button>
        <AlgorithmDrawer
          visible={visible}
          algorithmProjectId={3}
          algorithmId={3}
          onCancel={() => {
            setVisible(false);
          }}
          parameterVariables={[
            {
              name: 'extraField',
              required: true,
              value: '',
              display_name: '',
              comment: '',
              value_type: 'STRING',
            },
          ]}
        />
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```

## 子组件

### Button

为了方便起见，封装了点击按钮后，展示 Drawer 的逻辑，支持传递 text 来指定 button 的文案，并提供 children 来高度自定义孩子节点(在组件内部已经封装了 onClick 逻辑)

<API src="components/AlgorithmDrawer/index.tsx" exports='["_Button"]' hideTitle></API>

```tsx
import React, { useState } from 'react';
import { RecoilRoot } from 'recoil';
import { QueryClientProvider } from 'react-query';
import queryClient from 'shared/queryClient';
import AlgorithmDrawer from 'components/AlgorithmDrawer';

export default () => {
  return (
    <RecoilRoot>
      <QueryClientProvider client={queryClient}>
        <AlgorithmDrawer.Button
          text="Click me"
          algorithmProjectId={3}
          algorithmId={3}
          onCancel={() => {
            setVisible(false);
          }}
        />
        <br />
        <AlgorithmDrawer.Button
          algorithmProjectId={3}
          algorithmId={3}
          onCancel={() => {
            setVisible(false);
          }}
        >
          <span style={{ cursor: 'pointer' }}>Custom children</span>
        </AlgorithmDrawer.Button>
      </QueryClientProvider>
    </RecoilRoot>
  );
};
```
