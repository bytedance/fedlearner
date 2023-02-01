# SharedPageLayout

统一的 Content 页面布局,含有标题/中心标题/padding 等配置

> 注意 ⚠️: 因为 `<SharedPageLayout/>` 内部引入了 `recoil` 相关的函数，所以 Demo 代码中用 `<RecoilRoot/>` 作为根组件，防止报错。

> 主要原因是 `removeSidebar` 这个 props 属性导致，他设置`recoil`某个`atom`下的变量`hideSidebar`为 true。

> 现在最新隐藏侧边栏的方案（最新方案是在 React-Router 上配置 Layout 布局）已经不需要这个`removeSidebar`,所以使用了`@deprecated`进行标记，以后会把这个属性删除。

<API src="components/SharedPageLayout/index.tsx" exports='["default"]'></API>

## 默认

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## Title

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title">
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## CenterTitle

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" centerTitle="i am center title">
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## Tip

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" centerTitle="i am center title" tip="i am tip">
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## CardPadding

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" cardPadding={0}>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## isHideHeader

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" isHideHeader={true}>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## IsNestSpinFlexContainer

When isNestSpinFlexContainer is true

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import { Spin } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" isNestSpinFlexContainer={true}>
      <Spin loading={true}>
        <div>Chilren</div>
        <div>Chilren</div>
        <div>Chilren</div>
      </Spin>
    </SharedPageLayout>
  </RecoilRoot>
);
```

When isNestSpinFlexContainer is false

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import { Spin } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" isNestSpinFlexContainer={false}>
      <Spin loading={true}>
        <div>Chilren</div>
        <div>Chilren</div>
        <div>Chilren</div>
      </Spin>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## contentWrapByCard

When contentWrapByCard is true

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" contentWrapByCard={true}>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

When contentWrapByCard is false

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title" contentWrapByCard={false}>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## isShowFixedBottomLayout

isShowFixedBottomLayout 为 true 时，会显示固定在底部的 footer 布局，默认自带 2 个按钮（文案可以通过`bottomOkText`/`bottomCancelText`来更改），一个 tip 提示组件(文案可以通过`bottomTip`来更改，内部实际上使用[TitleWithIcon](/display/title-with-icon)来实现)

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout
      title="i am title"
      contentWrapByCard={true}
      isShowFixedBottomLayout={true}
      bottomOkText="Confirm"
      bottomCancelText="Cancel"
      bottomTip="I am tip"
      onBottomOkClick={() => alert('ok')}
      onBottomCancelClick={() => alert('cancel')}
    >
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

也可以通过`renderFixedBottomLayout`来自定义具体的渲染内容

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout
      title="i am title"
      contentWrapByCard={true}
      isShowFixedBottomLayout={true}
      renderFixedBottomLayout={() => {
        return <div>I am custom render layout</div>;
      }}
    >
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

## 子组件

### 常量

`PAGE_SECTION_PADDING` 被用作为 `cardPadding` 的默认值

```jsx | pure
export const PAGE_SECTION_PADDING = 20;
```

### RemovePadding

用作抵消 `SharedPageLayout` 卡片布局默认的 padding

```jsx | pure
export const RemovePadding = styled.div`
  margin: -${PAGE_SECTION_PADDING}px -${PAGE_SECTION_PADDING}px 0;
`;
```

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout, { RemovePadding } from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title">
      <RemovePadding>
        <div style={{ border: '1px solid red' }}>Chilren</div>
      </RemovePadding>

      <div style={{ border: '1px solid blue' }}>Chilren</div>
      <div style={{ border: '1px solid blue' }}>Chilren</div>

      <RemovePadding>
        <div style={{ border: '1px solid red' }}>Chilren</div>
      </RemovePadding>
    </SharedPageLayout>
  </RecoilRoot>
);
```

在项目中，常常与 Tabs 配合

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import { Tabs } from '@arco-design/web-react';
import SharedPageLayout, { RemovePadding } from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title">
      <RemovePadding>
        <Tabs>
          <Tabs.TabPane title="tab1" key="1" />
          <Tabs.TabPane title="tab2" key="2" />
        </Tabs>
      </RemovePadding>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```

### FormHeader

在 `RemovePadding`的基础上，显示卡片布局的标题

```jsx | pure
export const FormHeader = styled.h3`
  display: flex;
  height: 46px;
  font-size: 16px;
  line-height: 24px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--lineColor);
  margin: -${PAGE_SECTION_PADDING}px -${PAGE_SECTION_PADDING}px 0;
`;
```

```jsx
/**
 * compact: true
 */
import React from 'react';
import { RecoilRoot } from 'recoil';
import SharedPageLayout, { FormHeader } from 'components/SharedPageLayout';

export default () => (
  <RecoilRoot>
    <SharedPageLayout title="i am title">
      <FormHeader>Card title</FormHeader>
      <div>Chilren</div>
      <div>Chilren</div>
      <div>Chilren</div>
    </SharedPageLayout>
  </RecoilRoot>
);
```
