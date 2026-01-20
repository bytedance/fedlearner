# FileUpload

基于 [Arco Upload](xxx) 封装，具有限制文件大小，上传文件成功/失败回调功能

> 注意 ⚠️: 目前组件内部逻辑是根据 `action = /api/v2/files` 返回的结构来处理的，如果 action 换成其他地址可能会存在问题

<API src="components/FileUpload/index.tsx"></API>

也支持传入 [Arco Upload](xxx) 原有的 props

### UploadFileType

```jsx | pure
enum UploadFileType {
  Dataset = 'dataset'
}
```

### UploadFile

```jsx | pure
interface UploadFile<T = any> {
  uid: string;
  size: number;
  name: string;
  fileName?: string;
  lastModified?: number;
  lastModifiedDate?: Date;
  url?: string;
  status?: UploadFileStatus;
  percent?: number;
  thumbUrl?: string;
  originFileObj: RcFile;
  response?: T;
  error?: any;
  linkProps?: any;
  type: string;
  xhr?: T;
  preview?: string;
}
```

### UploadChangeParam

```jsx | pure
interface UploadChangeParam<T extends object = UploadFile> {
    file: T;
    fileList: UploadFile[];
    event?: {
        percent: number;
    };
}
```

## 常规用法

```tsx
import React, { useState } from 'react';
import FileUpload, { UploadFileType } from 'components/FileUpload';

export default () => {
  const [value, setValue] = useState([]);
  return (
    <>
      <FileUpload
        accept=".csv,.tfrecord,tar,.gz"
        kind={UploadFileType.Dataset}
        maxSize={1024 * 1024 * 100} // 100MB
        dp={0}
        onSuccess={(info) => console.log(info)}
        onError={(error) => console.log(error)}
      />
    </>
  );
};
```

## action

接口使用了 arco upload 组件演示的地址

```tsx
import React, { useState } from 'react';
import FileUpload, { UploadFileType } from 'components/FileUpload';

export default () => {
  const [value, setValue] = useState([]);
  return (
    <>
      <FileUpload
        action="https://www.mocky.io/v2/5cc8019d300000980a055e76"
        accept=".csv,.tfrecord,tar,.gz"
        kind={UploadFileType.Dataset}
        maxSize={1024 * 1024 * 100} // 100MB
        dp={0}
      />
    </>
  );
};
```
