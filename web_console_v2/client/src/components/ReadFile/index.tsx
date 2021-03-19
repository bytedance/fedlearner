import React, { useState, FC, useEffect } from 'react';
import styled from 'styled-components';
import { message, Upload } from 'antd';
import { useTranslation } from 'react-i18next';
import classNames from 'classnames';
import { MixinCommonTransition } from 'styles/mixins';
import { ReactComponent as FileIcon } from 'assets/images/file.svg';
import { RcFile } from 'antd/lib/upload';
import { isNil } from 'lodash';
import { PlusCircle, Delete } from 'components/IconPark';

const Container = styled.div`
  position: relative;
  min-height: 32px;
  border-radius: 2px;
`;
const WithoutFile = styled.div`
  ${MixinCommonTransition(['max-height', 'opacity'])};

  max-height: 400px;
  will-change: max-height;

  &.hidden {
    max-height: 0;
  }
`;
const File = styled.div`
  ${MixinCommonTransition(['opacity'])};

  position: absolute;
  top: 0;
  z-index: 2;
  display: flex;
  height: 32px;
  width: 100%;
  padding-left: 16px;
  padding-right: 12px;
  align-items: center;
  opacity: 0;
  pointer-events: none;

  &.visible {
    opacity: 1;
    pointer-events: initial;

    > .anticon-check-circle {
      animation: zoomIn 0.3s cubic-bezier(0.12, 0.4, 0.29, 1.46);
    }
  }

  > .filename {
    padding-left: 10px;
    flex: 1;
  }

  > .anticon-check-circle {
    color: var(--errorColor);
  }
`;
const DeleteFileBtn = styled.div`
  position: absolute;
  right: -20px;
  cursor: pointer;

  &:hover {
    color: var(--primaryColor);
  }
`;
const ContentInner = styled.div`
  padding: 20px 0 40px;
`;
const PlusIcon = styled.p`
  font-size: 16px;
`;
const UploadPlaceholder = styled.div`
  margin-bottom: 4px;
  line-height: 24px;
  font-size: 16px;
`;
const UploadHint = styled.small`
  display: block;
  font-size: 12px;
  line-height: 18px;
  color: var(--textColorSecondary);
`;
const DragUpload = styled(Upload.Dragger)`
  padding: 0;
`;

type Props = React.ComponentProps<typeof Upload> & {
  reader: (file: File) => Promise<any>;
  maxSize?: number; // unit: MB
  value?: any | null;
  onChange?: <T>(val: T, file?: File) => void;
  onRemoveFile?: (...args: any[]) => any;
};

const ReadFile: FC<Props> = ({ maxSize, value, reader, onRemoveFile, onChange, ...props }) => {
  const { beforeUpload } = props;

  const { t } = useTranslation();
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
    beforeUpload: onFileInput,
  };

  return (
    <Container>
      <File className={classNames({ visible: hasValue })}>
        <FileIcon />
        <span className="filename">{file?.name}</span>
        <DeleteFileBtn onClick={onDeleteClick}>
          <Delete />
        </DeleteFileBtn>
      </File>

      <DragUpload {...(uploadProps as any)}>
        <WithoutFile className={classNames({ hidden: hasValue })}>
          <ContentInner>
            <PlusIcon>
              <PlusCircle />
            </PlusIcon>

            <UploadPlaceholder>{t('upload.placeholder')}</UploadPlaceholder>

            <UploadHint>
              {t('upload.hint', { fileTypes: props.accept, maxSize: maxSize })}
            </UploadHint>
          </ContentInner>
        </WithoutFile>
      </DragUpload>
    </Container>
  );

  function onFileChange({ file, event }: any) {
    return reader(file)
      .then((result) => {
        onChange && onChange(result, file);
        setFile(file);
      })
      .catch((error) => {
        message.error(error.message);
      });
  }
  function onFileInput(file: RcFile, fileList: RcFile[]) {
    beforeUpload && beforeUpload(file, fileList);

    return false;
  }
  function onDeleteClick() {
    onRemoveFile && onRemoveFile(file);
    onChange && onChange(null as any);
    setFile(null as any);
  }
};

export default ReadFile;
