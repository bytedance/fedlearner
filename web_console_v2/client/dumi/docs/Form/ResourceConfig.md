# ResourceConfig

资源配置组件，基于 [Arco Collapse](https://arco.design/react/components/collapse#api) 和 [InputGroup](/form/input-group) 封装

不同的 `algorithmType` 算法类型，会显示不同的布局，目前有 2 大类，Tree 算法类型和 NN 算法类型。组件默认显示 Tree 算法类型的布局

<API src="components/ResourceConfig/index.tsx" exports='["default"]'></API>

### Option

```tsx | pure
type Value = {
  resource_type: ResourceTemplateType | `${ResourceTemplateType}`;
  master_cpu?: string;
  master_mem?: string;
  master_replicas?: string;
  ps_cpu?: string;
  ps_mem?: string;
  ps_replicas?: string;
  worker_cpu?: string;
  worker_mem?: string;
  worker_replicas?: string;
};

enum ResourceTemplateType {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low',
  CUSTOM = 'custom',
}

enum AlgorithmType {
  TREE_VERTICAL = 'TREE_VERTICAL',
  NN_VERTICAL = 'NN_VERTICAL',
  NN_HORIZONTAL = 'NN_HORIZONTAL',
}
```

## 常规用法

```tsx
import React, { useState } from 'react';
import ResourceConfig from 'components/ResourceConfig';

export default () => {
  return (
    <ResourceConfig
      defaultResourceType="medium"
      algorithmType="TREE_VERTICAL"
      onChange={(val) => {
        console.log('val', val);
      }}
    />
  );
};
```

## 受控模式

```tsx
import React, { useState } from 'react';
import ResourceConfig from 'components/ResourceConfig';

export default () => {
  const [value, setValue] = useState({
    master_cpu: '1000m',
    master_mem: '64Gi',
    master_replicas: '2',
    ps_cpu: '4000m',
    ps_mem: '16Gi',
    ps_replicas: '3',
    resource_type: 'custom',
    worker_cpu: '4000m',
    worker_mem: '128Gi',
    worker_replicas: '1',
  });
  return (
    <>
      <ResourceConfig
        value={value}
        algorithmType="NN_VERTICAL"
        onChange={(val) => {
          console.log('val', val);
          setValue(val);
        }}
      />
    </>
  );
};
```