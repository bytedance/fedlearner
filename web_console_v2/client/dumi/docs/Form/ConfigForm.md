# ConfigForm

动态渲染 [Form.Item](https://arco.design/react/components/form#formitem) 配置的表单组，支持[Collapse](https://arco.design/react/components/collapse#api) 包裹部分 Form.Item

<API src="components/ConfigForm/index.tsx"></API>

### ItemProps

```ts | pure
type ItemProps = {
  componentType?: 'Input' | 'TextArea' | 'InputNumber';
  componentProps?: object;
  render?: (props: Omit<ItemProps, 'render'>) => React.ReactNode;
} & FormItemProps;
```

## 常规用法

```tsx
import React from 'react';
import ConfigForm from 'components/ConfigForm';

const formItemList = [
  {
    label: '学习率',
    field: 'learning_rate',
    componentType: 'InputNumber',
  },
  {
    label: '迭代数',
    field: 'max_iters',
    componentType: 'InputNumber',
  },
  {
    label: '深度',
    field: 'max_depth',
    componentType: 'InputNumber',
  },
  {
    label: 'L2惩罚系数',
    field: 'l2_regularization',
    componentType: 'InputNumber',
  },
  {
    label: '最大分箱数量',
    field: 'max_bins',
    componentType: 'InputNumber',
  },
  {
    label: '线程池大小',
    field: 'num_parallel',
    componentType: 'InputNumber',
  },
];
const collapseFormItemList = [
  {
    label: '高级配置1',
    field: 'p1',
    componentType: 'Input',
  },
  {
    label: '高级配置2',
    field: 'p2',
    componentType: 'TextArea',
  },
  {
    label: '高级配置3',
    field: 'p3',
  },
  {
    label: '高级配置4',
    field: 'p4',
  },
];

export default () => {
  return (
    <ConfigForm
      cols={2}
      formItemList={formItemList}
      collapseFormItemList={collapseFormItemList}
      isDefaultOpenCollapse={false}
      collapseTitle="高级配置"
      onChange={(values) => {
        console.log(values);
      }}
    />
  );
};
```

## Cols

支持指定每行渲染多少个 Form.Item，取值范围为 cols = 1 | 2 | 3 | 4 | 6 | 8 | 12

```tsx
import React from 'react';
import ConfigForm from 'components/ConfigForm';

const formItemList = [
  {
    label: '学习率',
    field: 'learning_rate',
    componentType: 'InputNumber',
  },
  {
    label: '迭代数',
    field: 'max_iters',
    componentType: 'InputNumber',
  },
  {
    label: '深度',
    field: 'max_depth',
    componentType: 'InputNumber',
  },
  {
    label: 'L2惩罚系数',
    field: 'l2_regularization',
    componentType: 'InputNumber',
  },
  {
    label: '最大分箱数量',
    field: 'max_bins',
    componentType: 'InputNumber',
  },
  {
    label: '线程池大小',
    field: 'num_parallel',
    componentType: 'InputNumber',
  },
];
const collapseFormItemList = [
  {
    label: '高级配置1',
    field: 'p1',
    componentType: 'Input',
  },
  {
    label: '高级配置2',
    field: 'p2',
    componentType: 'TextArea',
  },
  {
    label: '高级配置3',
    field: 'p3',
  },
  {
    label: '高级配置4',
    field: 'p4',
  },
];

export default () => {
  return (
    <ConfigForm
      cols={4}
      formItemList={formItemList}
      collapseFormItemList={collapseFormItemList}
      isDefaultOpenCollapse={false}
      collapseTitle="高级配置"
      onChange={(values) => {
        console.log(values);
      }}
    />
  );
};
```

## Render

componentType 只支持 3 种组件，`Input`、`TextArea`、`InputNumber`，分别为 Arco 的 Input，Input.TextArea，InputNumber 组件，如果需要自定义渲染 Form.Item 包裹的组件的话，可以传入 render 函数，他只接受 1 个参数`componentProps`

render 的优先级比 componentType 高

```tsx
import React from 'react';
import { Switch } from '@arco-design/web-react';
import ConfigForm from 'components/ConfigForm';

const formItemList = [
  {
    label: '切换1',
    field: 'switch1',
    render(props) {
      return <Switch {...props} />;
    },
  },
  {
    label: '切换（禁用）',
    field: 'switch2',
    componentProps: {
      disabled: true,
    },
    render(props) {
      return <Switch {...props} />;
    },
  },
];

export default () => {
  return (
    <ConfigForm
      formItemList={formItemList}
      onChange={(values) => {
        console.log(values);
      }}
    />
  );
};
```
