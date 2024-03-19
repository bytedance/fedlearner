# BlockRadio

块状单选框

<API src="components/_base/BlockRadio/index.tsx"></API>

### Option

每个 item 格式定义

```jsx | pure
type Option = {
  /** form value */
  value: any,
  /** display label */
  label: string,
  disabled?: boolean,
  /** extra data, one of the function(renderBlockInner) arguments */
  data?: any,
  /** extra tip, only work in <BlockRadio.WithTip/>'s options prop */
  tip?: string,
};
```

## 常规用法

默认占用一整行，平分，gap = 16

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
      />
    </>
  );
};
```

## Gap

gap = 64

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio
        gap={64}
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
      />
    </>
  );
};
```

## IsCenter

单选项展示内容是否居中显示

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio
        isCenter={true}
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
      />
    </>
  );
};
```

## Disabled

disabled = true

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio
        disabled={true}
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
      />
    </>
  );
};
```

## IsVertical

isVertical = true

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio
        isVertical={true}
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
      />
    </>
  );
};
```

## IsOneHalfMode

isOneHalfMode = true

```jsx
import React, { useState } from 'react';
import { Grid, Form, Input } from '@arco-design/web-react';
import BlockRadio from 'components/_base/BlockRadio';
const { Row, Col } = Grid;

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <Form labelCol={{ span: 24 }} wrapperCol={{ span: 24 }} labelAlign="left">
        <BlockRadio
          isOneHalfMode={true}
          value={value}
          options={options}
          onChange={(val) => {
            setValue(val);
          }}
        />
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="file_ext" label="file_ext">
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="file_type" label="file_type">
              <Input />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </>
  );
};
```

isOneHalfMode = false

```jsx
import React, { useState } from 'react';
import { Grid, Form, Input } from '@arco-design/web-react';
import BlockRadio from 'components/_base/BlockRadio';
const { Row, Col } = Grid;

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <Form labelCol={{ span: 24 }} wrapperCol={{ span: 24 }} labelAlign="left">
        <BlockRadio
          isOneHalfMode={false}
          value={value}
          options={options}
          onChange={(val) => {
            setValue(val);
          }}
        />
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="file_ext" label="file_ext">
              <Input />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="file_type" label="file_type">
              <Input />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </>
  );
};
```

## BeforeChange

beforeChange 可以拦截 onChange 的事件触发，如果返回 beforeChange 返回 `false` 或者 `Promise.resolve(false)` 的话,则不会触发 onChange 事件

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';
import Modal from 'components/Modal';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
        beforeChange={() => {
          return new Promise((resolve) => {
            Modal.confirm({
              title: '确认变更',
              content: '确认这样做吗？',
              onOk() {
                resolve(true);
              },
              onCancel() {
                resolve(false);
              },
            });
          });
        }}
      />
    </>
  );
};
```

## RenderBlockInner

自定义 inner 内容渲染

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';

const options = [
  {
    value: '1',
    label: 'label1',
  },
  {
    value: '2',
    label: 'label2',
  },
  {
    value: '3',
    label: 'label3',
  },
  {
    value: '4',
    label: 'label4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
        renderBlockInner={(item, { label, data, isActive }) => {
          return (
            <div>
              {label}
              <div>footer</div>
            </div>
          );
        }}
      />
    </>
  );
};
```

## 子组件

### BlockRadio.WithTip

重写 renderBlockInner，达到能显示 tip 的效果

```jsx | pure
const WithTip: FC<Props> = (props) => {
  return (
    <BlockRadio
      renderBlockInner={(item, { label, isActive }) => {
        return (
          <ContainerWithTips>
            <Label>{item.label}</Label>
            <LabelTips>{item.tip}</LabelTips>
          </ContainerWithTips>
        );
      }}
      {...props}
    />
  );
};
BlockRadio.WithTip = WithTip;
```

BlockRadio.WithTip 的 options 比 BlockRadio 多了一个 tip 字段

```jsx
import React, { useState } from 'react';
import BlockRadio from 'components/_base/BlockRadio';

const options = [
  {
    value: '1',
    label: 'label1',
    tip: 'tip1',
  },
  {
    value: '2',
    label: 'label2',
    tip: 'tip2',
  },
  {
    value: '3',
    label: 'label3',
    tip: 'tip3',
  },
  {
    value: '4',
    label: 'label4',
    tip: 'tip4',
  },
];

export default () => {
  const [value, setValue] = useState(options[0].value);
  return (
    <>
      <BlockRadio.WithTip
        value={value}
        options={options}
        onChange={(val) => {
          setValue(val);
        }}
      />
    </>
  );
};
```
