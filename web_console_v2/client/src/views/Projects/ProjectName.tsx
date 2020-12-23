import React, { ReactElement } from 'react'
import styled, { CSSProperties } from 'styled-components'
import { Tooltip } from 'antd'
import { MixinEllipsis } from 'styles/mixins'

const Container = styled.div`
  ${MixinEllipsis()}

  color: var(--gray10);
  font-weight: 500;
  font-size: 15px;
  line-height: 40px;
  margin-left: 16px;
`

interface CreateTimeProps {
  text: string
  style?: CSSProperties
}

function ProjectName({ text, style }: CreateTimeProps): ReactElement {
  return (
    <Tooltip title={text}>
      <Container style={style}>{text}</Container>
    </Tooltip>
  )
}

export default ProjectName
