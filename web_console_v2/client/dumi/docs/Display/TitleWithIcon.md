# TitleWithIcon

显示标题 + Icon 的组件,带有 tip 提示功能

<API src="components/TitleWithIcon/index.tsx"></API>

## 常规使用

```jsx
import React from 'react';
import TitleWithIcon from 'components/TitleWithIcon';

export default () => (
  <>
    <TitleWithIcon title="title" />
  </>
);
```

## IsShowIcon

```jsx
import React from 'react';
import TitleWithIcon from 'components/TitleWithIcon';

export default () => (
  <>
    <TitleWithIcon title="title" isShowIcon={true} />
  </>
);
```

## IsLeftIcon

```jsx
import React from 'react';
import TitleWithIcon from 'components/TitleWithIcon';

export default () => (
  <>
    <TitleWithIcon title="title" isLeftIcon={true} isShowIcon={true} />
    <TitleWithIcon title="title" isLeftIcon={false} isShowIcon={true} />
  </>
);
```

## Tip

isShowIcon = false 时，不显示 tip

```jsx
import React from 'react';
import TitleWithIcon from 'components/TitleWithIcon';

export default () => (
  <>
    <TitleWithIcon title="title" isLeftIcon={true} isShowIcon={false} tip="tip" />
    <TitleWithIcon title="title" isLeftIcon={true} isShowIcon={true} tip="tip" />
    <TitleWithIcon title="title" isLeftIcon={false} isShowIcon={true} tip="tip" />
  </>
);
```

## Icon

```jsx
import React from 'react';
import TitleWithIcon from 'components/TitleWithIcon';
import { InfoCircle } from 'components/IconPark';

export default () => (
  <>
    <TitleWithIcon title="title" isLeftIcon={true} isShowIcon={true} tip="tip" icon={InfoCircle} />
    <TitleWithIcon title="title" isLeftIcon={false} isShowIcon={true} tip="tip" icon={InfoCircle} />
  </>
);
```

## TextColor

```jsx
import React from 'react';
import TitleWithIcon from 'components/TitleWithIcon';
import { InfoCircle } from 'components/IconPark';

export default () => (
  <>
    <TitleWithIcon
      title="title"
      isLeftIcon={true}
      isShowIcon={true}
      tip="tip"
      icon={InfoCircle}
      textColor="red"
    />
    <TitleWithIcon
      title="title"
      isLeftIcon={false}
      isShowIcon={true}
      tip="tip"
      icon={InfoCircle}
      textColor="red"
    />
  </>
);
```
