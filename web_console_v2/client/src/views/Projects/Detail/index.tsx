import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { Drawer } from 'antd'
import { Project } from 'typings/project'
import DetailBody from './DetailBody'
import DetailHeader from './DetailHeader'
import { ReactComponent as CloseIcon } from 'assets/images/close-icon.svg'

const CloseIconStyle = styled.div`
  height: 24px;
  width: 24px;
  background: #f2f3f5;
  border-radius: 2px;
  padding: 3px;
  margin-top: -2px;
  &:hover {
    background: #e5e6eb;
  }
`
interface DetailProps {
  visible: boolean
  title: string
  onClose: () => void
  project: Project
}

function Close(): ReactElement {
  return (
    <CloseIconStyle>
      <CloseIcon />
    </CloseIconStyle>
  )
}

function Detail({ visible, onClose, project }: DetailProps): ReactElement {
  return (
    <Drawer
      placement="right"
      closable={true}
      width={880}
      zIndex={1999}
      closeIcon={<Close />}
      visible={visible}
      onClose={onClose}
      title={<DetailHeader project={project} />}
    >
      <DetailBody project={project} />
    </Drawer>
  )
}

export default Detail
