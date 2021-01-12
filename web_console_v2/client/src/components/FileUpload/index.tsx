import React, { useState } from 'react'
import styled from 'styled-components'
import { Upload } from 'antd'
import { PlusOutlined, CheckCircleFilled, DeleteFilled } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import classNames from 'classnames'
import { MixinCommonTransition } from 'styles/mixins'
import { ReactComponent as FileIcon } from 'assets/images/file.svg'

type Props = {
  maxSize?: string
  value?: any
  onRemoveFile?: (...args: any[]) => any
} & React.ComponentProps<typeof Upload>

const Container = styled.div`
  min-height: 32px;
  background-color: var(--gray2);
  border-radius: 2px;
`
const WithoutFile = styled.div`
  ${MixinCommonTransition(['max-height', 'opacity'])};

  max-height: 400px;
  will-change: max-height;

  &.hidden {
    max-height: 0;
  }
`
const FileItem = styled.div`
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
      /* animation-name: diffZoomIn1; */
      animation: zoomIn 0.3s cubic-bezier(0.12, 0.4, 0.29, 1.46);
    }
  }

  > .filename {
    padding-left: 10px;
    flex: 1;
  }

  > .anticon-check-circle {
    color: var(--successColor);
  }
`
const DeleteFileBtn = styled.div`
  position: absolute;
  right: -20px;
  cursor: pointer;

  &:hover {
    color: var(--primaryColor);
  }
`
const ContentInner = styled.div`
  padding: 20px 0 40px;
`
const PlusIcon = styled.p`
  font-size: 16px;
`
const UploadPlaceholder = styled.div`
  margin-bottom: 4px;
  line-height: 24px;
  font-size: 16px;
`
const UploadHint = styled.small`
  display: block;
  font-size: 12px;
  line-height: 18px;
  color: var(--textColorSecondary);
`
const DragUpload = styled(Upload.Dragger)`
  padding: 0;
`

const FileUpload = ({ maxSize, value, onRemoveFile, ...props }: Props) => {
  const { t } = useTranslation()
  const hasValue = !!value
  const [filename, setFilename] = useState('')

  return (
    <Container>
      <FileItem className={classNames({ visible: hasValue })}>
        <FileIcon />
        <span className="filename">{filename}</span>
        <DeleteFileBtn onClick={onRemoveFile}>
          <DeleteFilled />
        </DeleteFileBtn>
      </FileItem>
      <DragUpload disabled={hasValue} {...(props as any)} onChange={onFileChange}>
        <WithoutFile className={classNames({ hidden: hasValue })}>
          <ContentInner>
            <PlusIcon>
              <PlusOutlined />
            </PlusIcon>

            <UploadPlaceholder>{t('upload.placeholder')}</UploadPlaceholder>

            <UploadHint>
              {t('upload.hint', { fileTypes: props.accept, maxSize: maxSize })}
            </UploadHint>
          </ContentInner>
        </WithoutFile>
      </DragUpload>
    </Container>
  )

  function onFileChange({ file }: any) {
    setFilename(file.name)
  }
}

export default FileUpload
