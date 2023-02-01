# InfoItem

显示标题 + Tag 内容的组件，其中标题充当 Header，内容充当 Footer，并带有 Tag 效果

<API src="components/InfoItem/index.tsx"></API>

## 常规使用

```jsx
import React from 'react';
import InfoItem from 'components/InfoItem';

export default () => (
  <>
    <div style={{ display: 'flex', width: 400, justifyContent: 'space-between' }}>
      <InfoItem title="title1" value="value1" />
      <InfoItem title="title2" value="value2" />
      <InfoItem title="title3" value="value3" valueColor="blue" />
    </div>
  </>
);
```

## IsBlock

```jsx
import React from 'react';
import InfoItem from 'components/InfoItem';

export default () => (
  <>
    <InfoItem title="title1" value="value1" isBlock={true} />
    <InfoItem title="title2" value="value2" isBlock={true} />
    <InfoItem title="title3" value="value3" isBlock={true} />
  </>
);
```

## Value

value 可以传入任意 React 组件

例如，要实现 Copy 功能,支持 Copy 拷贝的组件

```jsx
import React from 'react';
import InfoItem from 'components/InfoItem';
import ClickToCopy from 'components/ClickToCopy';
import { Copy } from 'components/IconPark';

export default () => (
  <>
    <InfoItem
      title="title1"
      isComponentValue={true}
      value={
        <ClickToCopy text="value1" successTip="Copy success" failTip="Copy fail">
          <span>value1</span>
          <Copy />
        </ClickToCopy>
      }
    />
  </>
);
```

## IsInputMode

isInputMode = true 时，value 类似 defaultValue 的作用

配合 onInputBlur 可以获取 input 的内容

```jsx
import React from 'react';
import InfoItem from 'components/InfoItem';

export default () => (
  <>
    <InfoItem
      title="title1"
      value="defaultValue1"
      isInputMode={true}
      onInputBlur={(val) => {
        console.log(val);
      }}
    />
  </>
);
```

## OnClick

isInputMode = true 时，onClick 不会生效

```jsx
import React from 'react';
import InfoItem from 'components/InfoItem';

export default () => (
  <>
    <InfoItem
      title="title1"
      value="value1"
      isInputMode={true}
      isBlock={true}
      onInputBlur={(val) => {
        console.log(val);
      }}
      onClick={(val) => {
        alert('value1');
      }}
    />

    <InfoItem
      title="title1"
      value="value2"
      onClick={(val) => {
        alert('value2');
      }}
    />
  </>
);
```
