# CountTime

计时器组件,支持倒计时 CountDown / 计时 CountUp,有 renderProps 模式

<API src="components/CountTime/index.tsx" exports='["default"]'></API>

## 常规使用

### CountUp

```tsx
import React from 'react';
import CountTime from 'components/CountTime';

export default () => (
  <>
    <div>Count up begins at 10 second</div>
    <CountTime time={10} />
  </>
);
```

### CountDown

```tsx
import React from 'react';
import CountTime from 'components/CountTime';

export default () => (
  <>
    <div>Count down begins at 10 second</div>
    <CountTime time={10} isCountDown={true} />
  </>
);
```

## IsOnlyShowSecond

```tsx
import React from 'react';
import CountTime from 'components/CountTime';

export default () => (
  <>
    <div>Count down begins at 100 second</div>
    <CountTime time={100} isCountDown={true} isOnlyShowSecond={true} />
  </>
);
```

## IsStatic

isStatic 为 true 时，停止计时器

```tsx
import React from 'react';
import CountTime from 'components/CountTime';

export default () => (
  <>
    <div>Count down begins at 10 second</div>
    <CountTime time={10} isStatic={true} />
  </>
);
```

根据这个特性，可以动态控制计时器的开始和暂停

```tsx
import React, { useState } from 'react';
import CountTime from 'components/CountTime';

export default () => {
  const [isStatic, setIsStatic] = useState(false);

  return (
    <>
      <div>Count down begins at 10 second</div>
      <CountTime time={10} isCountDown={true} isStatic={isStatic} />

      <button
        onClick={() => {
          setIsStatic((prevState) => !prevState);
        }}
      >
        Toggle timer
      </button>
    </>
  );
};
```

## IsResetOnChange

当 isResetOnChange = true,并且 isStatic 从 false 变为 true 时，会重置计时器为传入的 time，并停止计时器

```tsx
import React, { useState } from 'react';
import CountTime from 'components/CountTime';

export default () => {
  const [isStatic, setIsStatic] = useState(false);

  return (
    <>
      <div>Count down begins at 10 second</div>
      <CountTime time={10} isCountDown={true} isStatic={isStatic} isResetOnChange={true} />

      <button
        onClick={() => {
          setIsStatic((prevState) => !prevState);
        }}
      >
        Reset and toggle timer
      </button>
    </>
  );
};
```

## IsRenderPropsMode

当 isRenderPropsMode = true，可以使用 render props 模式，此时可以在 children 中传入一个函数,格式为`(formatted, noFormattedTime) => React.ReactNode`

```tsx
import React from 'react';
import CountTime from 'components/CountTime';

export default () => {
  return (
    <>
      <div>Count down begins at 10 second</div>
      <CountTime time={10} isStatic={false} isCountDown={true} isRenderPropsMode={true}>
        {(formattedTime: any, time: any) => {
          return <div>current is: {time}s</div>;
        }}
      </CountTime>
    </>
  );
};
```

## OnCountDownFinish

当 isCountDown = true，并且倒计时首次进入 0 秒时，会触发 1 次 onCountDownFinish 函数

```tsx
import React from 'react';
import CountTime from 'components/CountTime';

export default () => {
  return (
    <>
      <div>Count down begins at 10 second</div>
      <CountTime
        time={10}
        isCountDown={true}
        onCountDownFinish={() => {
          console.log('onCountDownFinish');
        }}
      />
    </>
  );
};
```
