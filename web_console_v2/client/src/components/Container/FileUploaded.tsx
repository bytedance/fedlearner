import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { ReactComponent as FileSvg } from 'assets/images/file.svg'
import TrashCan from './TrashCan'
import { Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'

const LoadingIcon = <LoadingOutlined style={{ fontSize: 14 }} spin />

const Container = styled.div`
  height: 36px;
  padding: 8px 12px;
  background: var(--gray1);
  border-radius: 2px;
  position: relative;
  display: flex;
`
const FileSvgWrapper = styled.div`
  &::after {
    content: 'g';
    font-family: Nunito Sans;
    font-size: 14px;
    color: #ffffff;
    display: inline-block;
    position: relative;
    left: -12px;
    top: -5px;
  }
`

const TrashCanWrapper = styled.div`
  position: absolute;
  left: 345px;
  top: 10px;
`

const FileNameContainer = styled.div`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 260px;
  font-family: Nunito Sans;
  font-size: 14px;
  line-height: 20px;
  color: var(--gray10);
`
const SpinStyle = styled(Spin)`
  margin-top: -1px;
  margin-left: 10px;
`

interface Props {
  onDelete: () => void
  fileName: string
  loading: boolean
}

interface FileNameProps {
  fileName: string
}

function FileName({ fileName }: FileNameProps): ReactElement {
  return <FileNameContainer>{fileName}</FileNameContainer>
}

function FileUploaded({ onDelete, fileName, loading }: Props): ReactElement {
  return (
    <Container>
      <FileSvgWrapper>
        <FileSvg />
      </FileSvgWrapper>
      <FileName fileName={fileName} />
      {loading ? <SpinStyle indicator={LoadingIcon} /> : null}
      <TrashCanWrapper>
        <TrashCan
          onClick={() => {
            onDelete()
          }}
        />
      </TrashCanWrapper>
    </Container>
  )
}

export default FileUploaded
