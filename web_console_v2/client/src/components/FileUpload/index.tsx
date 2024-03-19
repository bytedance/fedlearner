/* istanbul ignore file */

import { Message, Upload, UploadProps } from '@arco-design/web-react';
import { PlusCircle } from 'components/IconPark';
import React, { FC, useState } from 'react';
import { isNil, omit } from 'lodash-es';
import { humanFileSize } from 'shared/file';
import { getJWTHeaders } from 'shared/helpers';
import { UploadItem } from '@arco-design/web-react/es/Upload';
import styles from './index.module.less';

export enum UploadFileType {
  Dataset = 'dataset',
}

export type UploadFile = {
  /**
   * File display name with folder displayed in code editor.
   *
   * Examples: "test/test.py","syslib.bin"
   */
  display_file_name: string;
  /** Internal store location for uploaded file */
  internal_path: string;
  /** Internal store parent directory for upload file */
  internal_directory: string;
  /**
   * File content that will be visible and editable for users
   *
   * Applicable only to human-readable text files
   */
  content?: string;
};

type Props = Omit<UploadProps, 'action' | 'headers' | 'onChange'> & {
  /** Path string */
  value?: string[];
  /** Path string list */
  onChange?: (val: UploadFile[]) => void;
  /** Will be as http post body data, i.e. { kind } */
  kind?: UploadFileType;
  action?: UploadProps['action'];
  headers?: UploadProps['headers'];
  /** Upload success */
  onSuccess?: (info: UploadItem) => void;
  /** Upload error */
  onError?: (error: any) => void;
  /** Max file size */
  maxSize?: number;
  maxCount?: number;
  /**
   * File size unit
   *
   * True - 1024
   *
   * False - 1000
   */
  isBinaryUnit?: boolean;
  /** Number of decimal places to display maxSize */
  dp?: number;
};

const FileUpload: FC<Props> = ({
  kind,
  action = '/api/v2/files',
  headers,
  onSuccess,
  onError,
  onChange,
  value,
  maxSize,
  isBinaryUnit = true,
  dp = 1,
  ...props
}) => {
  const [uidToPathMap, setMap] = useState<{ [key: string]: UploadFile }>({});

  return (
    <Upload
      drag={true}
      data={kind ? { kind } : undefined}
      limit={props.maxCount}
      headers={{ ...getJWTHeaders(), ...headers }}
      {...props}
      action={action}
      multiple
      onChange={onUploadChange}
      onRemove={onFileRemove}
      beforeUpload={beforeFileUpload}
    >
      <div className={styles.file_upload_inner}>
        <PlusCircle className={styles.plus_icon} />
        <div className={styles.file_upload_placeholder}>点击或拖拽文件到此处上传</div>
        <small className={styles.file_upload_tip}>
          {props.accept && `请上传${props.accept.split(',').join('/')}格式文件`}
          {props.accept && maxSize && `，`}
          {maxSize && `大小不超过${humanFileSize(maxSize, !isBinaryUnit, dp)}`}
        </small>
      </div>
    </Upload>
  );

  function onUploadChange(fileList: UploadItem[], info: UploadItem) {
    const { status, uid, originFile, response } = info;

    if (status === 'done') {
      onSuccess?.(info);
      const uploadedFile = (response as any)?.data?.uploaded_files[0];

      let nextMap: typeof uidToPathMap;

      // Will replace current one when maxCount is 1
      if (props.maxCount === 1) {
        nextMap = { [uid]: uploadedFile };
      } else {
        nextMap = { ...uidToPathMap, [uid]: uploadedFile };
      }
      setMap(nextMap);
      onChange?.(Object.values(nextMap));
    } else if (status === 'error') {
      Message.error(`${originFile?.name} 上传失败`);
      onError?.(originFile);
    }
  }
  function onFileRemove(file: UploadItem) {
    const { uid } = file;

    if (uidToPathMap[uid]) {
      const path = uidToPathMap[uid];
      const index = value?.findIndex((item) => item === path.internal_path);

      if (!isNil(index) && index > -1) {
        const next = [...(value ?? [])];
        next.splice(index, 1);

        const newMap = omit(uidToPathMap, uid);
        setMap(newMap);

        onChange?.(
          next.map((item) => {
            return {
              display_file_name: item,
              internal_path: item,
              internal_directory: item,
            };
          }),
        );
      }
    }
  }
  function beforeFileUpload(file: File, filesList: File[]) {
    if (maxSize && file.size > maxSize) {
      Message.warning(`文件大小不能超过 ${humanFileSize(maxSize, !isBinaryUnit, dp)}`);
      return false;
    }
    return props.beforeUpload ? props.beforeUpload(file, filesList) : true;
  }
};

export default FileUpload;
