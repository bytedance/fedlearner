# StateIndicator

显示状态的组件，具有显示颜色圆点 + 状态文本 + 提示语 + Hover 操作+Tag 模式的功能，常与 Table 配合，作为某个 Col 展示

<API src="components/StateIndicator/index.tsx"></API>

### StateTypes

```jsx | pure
type StateTypes =
  | 'processing'
  | 'success'
  | 'warning'
  | 'error'
  | 'default'
  | 'gold'
  | 'lime'
  | 'unknown'
  | 'pending_accept'
  | 'deleted';
```

### ActionItem

```jsx | pure
interface ActionItem {
  /** Display Label */
  label: string;
  onClick?: () => void;
  /** Sometimes you need to disable the button */
  disabled?: boolean;
  /** Sometimes you want a hint when the button is disabled */
  disabledTip?: string;
  /** Danger button style, red color */
  danger?: boolean;
}
```

## 常规使用

```jsx
import React from 'react';
import StateIndicator from 'components/StateIndicator';

export default () => (
  <>
    <StateIndicator type="default" text="default" />
    <StateIndicator type="error" text="error" />
    <StateIndicator type="processing" text="processing" />
    <StateIndicator type="success" text="success" />
    <StateIndicator type="warning" text="warning" />
    <StateIndicator type="gold" text="gold" />
    <StateIndicator type="lime" text="lime" />
    <StateIndicator type="unknown" text="unknown" />
    <StateIndicator type="pending_accept" text="pending_accept" />
  </>
);
```

## Tip

tip 会默认居中(Placement top)，注意容器 width 宽度

```jsx
import React from 'react';
import StateIndicator from 'components/StateIndicator';

export default () => (
  <>
    <div>
      <StateIndicator type="default" text="default" tip="tip" />
      <StateIndicator type="error" text="error" tip="tip" />
      <StateIndicator type="processing" text="processing" tip="tip" />
      <StateIndicator type="success" text="success" tip="tip" />
      <StateIndicator type="warning" text="warning" tip="tip" />
      <StateIndicator type="gold" text="gold" tip="tip" />
      <StateIndicator type="lime" text="lime" tip="tip" />
      <StateIndicator type="unknown" text="unknown" tip="tip" />
      <StateIndicator type="pending_accept" text="pending_accept" tip="tip" />
    </div>
  </>
);
```

## ActionList

Hover 上去会显示具体的操作

```jsx
import React from 'react';
import StateIndicator from 'components/StateIndicator';

const actionList = [
  {
    label: 'Delete',
    onClick: () => {
      alert('Delete');
    },
  },
  {
    label: 'Log',
    onClick: () => {
      alert('Log');
    },
  },
  {
    label: 'Refetch',
    onClick: () => {
      alert('Refetch');
    },
    isLoading: true,
  },
];

export default () => (
  <>
    <StateIndicator type="default" text="default" actionList={actionList} />
    <StateIndicator type="error" text="error" actionList={actionList} />
    <StateIndicator type="processing" text="processing" actionList={actionList} />
    <StateIndicator type="success" text="success" actionList={actionList} />
    <StateIndicator type="warning" text="warning" actionList={actionList} />
    <StateIndicator type="gold" text="gold" actionList={actionList} />
    <StateIndicator type="lime" text="lime" actionList={actionList} />
    <StateIndicator type="unknown" text="unknown" actionList={actionList} />
    <StateIndicator type="pending_accept" text="pending_accept" actionList={actionList} />
  </>
);
```

## Tag

Tag 单纯是[Arco Tag](https://arco.design/react/components/tag#api)组件，没有 tip/actionList 的功能

```jsx
import React from 'react';
import StateIndicator from 'components/StateIndicator';

export default () => (
  <>
    <StateIndicator type="default" text="default" tag={true} containerStyle={{ marginRight: 8 }} />
    <StateIndicator type="error" text="error" tag={true} containerStyle={{ marginRight: 8 }} />
    <StateIndicator
      type="processing"
      text="processing"
      tag={true}
      containerStyle={{ marginRight: 8 }}
    />
    <StateIndicator type="success" text="success" tag={true} containerStyle={{ marginRight: 8 }} />
    <StateIndicator type="warning" text="warning" tag={true} containerStyle={{ marginRight: 8 }} />
    <StateIndicator type="gold" text="gold" tag={true} containerStyle={{ marginRight: 8 }} />
    <StateIndicator type="lime" text="lime" tag={true} containerStyle={{ marginRight: 8 }} />
    <StateIndicator type="unknown" text="unknown" tag={true} containerStyle={{ marginRight: 8 }} />
    <StateIndicator
      type="pending_accept"
      text="pending_accept"
      tag={true}
      containerStyle={{ marginRight: 8 }}
    />
  </>
);
```

## AfterText

afterText 支持传递一个字符串，它会默认显示一个[Arco Button](https://arco.design/react/components/button#api)组件，并点击后会调用`onAfterTextClick`回调

```jsx
import React from 'react';
import StateIndicator from 'components/StateIndicator';

export default () => (
  <>
    <StateIndicator
      type="warning"
      text="unpublish"
      afterText="publish"
      onAfterTextClick={() => alert('publish')}
    />
  </>
);
```

afterText 也支持传递一个 React.ReactNode 类型（优先级比 string 字符串低），自定义渲染后面的内容，此时`onAfterTextClick`失效

```jsx
import React from 'react';
import StateIndicator from 'components/StateIndicator';

export default () => (
  <>
    <StateIndicator
      type="warning"
      text="unpublish"
      afterText={<div style={{ color: 'red' }}>I'm custom afterText</div>}
    />
  </>
);
```
