/* istanbul ignore file */

import React, { useState, FC, useEffect } from 'react';
import { Message, Upload } from '@arco-design/web-react';
import { ReactComponent as FileIcon } from 'assets/images/file.svg';
import { UploadItem } from '@arco-design/web-react/es/Upload';
import { isNil } from 'lodash-es';
import { PlusCircle, Delete } from 'components/IconPark';
import styles from './index.module.less';

type Props = React.ComponentProps<typeof Upload> & {
  reader: (file: File) => Promise<any>;
  maxSize?: number; // unit: MB
  value?: any | null;
  onChange?: <T>(val: T, file?: File) => void;
  onRemoveFile?: (...args: any[]) => any;
};

const ReadFile: FC<Props> = ({ maxSize, value, reader, onRemoveFile, onChange, ...props }) => {
  const [file, setFile] = useState<File>();

  const hasValue = Boolean(value);

  useEffect(() => {
    if (isNil(value)) {
      setFile(null as any);
    }
  }, [value]);
  const uploadProps = {
    ...props,
    disabled: hasValue || props.disabled,
    showUploadList: false,
    onChange: onFileChange,
  };

  return (
    <div className={styles.read_file_container}>
      <div className={`${styles.read_file} ${hasValue && styles.visible}`}>
        <FileIcon />
        <span className="filename">{file?.name}</span>
        <div className={styles.delete_file_btn} onClick={onDeleteClick}>
          <Delete />
        </div>
      </div>

      <Upload className={styles.read_file_upload} {...(uploadProps as any)} drag={true}>
        <div className={`${styles.read_file_without_upload} ${hasValue && styles.hidden}`}>
          <div className={styles.read_file_content_inner}>
            <p className={styles.read_file_plus_icon}>
              <PlusCircle />
            </p>

            <div className={styles.read_file_upload_placeholder}>点击或拖拽文件到此处上传</div>

            <small className={styles.read_file_upload_hint}>
              {maxSize || maxSize === 0
                ? `请上传${props.accept}格式文件，大小不超过${maxSize}MB`
                : `请上传${props.accept}格式文件`}
            </small>
          </div>
        </div>
      </Upload>
    </div>
  );

  function onFileChange(fileList: UploadItem[], { originFile: file }: UploadItem) {
    if (!file) return;
    if ((maxSize || maxSize === 0) && file.size > maxSize * 1024 * 1024) {
      Message.warning(`大小不超过${maxSize}MB!`);
      return;
    }

    return reader(file)
      .then((result) => {
        onChange && onChange(result, file);
        setFile(file);
      })
      .catch((error) => {
        Message.error(error.message);
      });
  }

  function onDeleteClick() {
    onRemoveFile && onRemoveFile(file);
    onChange && onChange(null as any);
    setFile(null as any);
  }
};

export default ReadFile;
