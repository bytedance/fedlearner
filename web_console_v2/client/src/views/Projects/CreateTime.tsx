import React, { ReactElement } from 'react'
import styled, { CSSProperties } from 'styled-components'
import dayjs from 'dayjs'

const Container = styled.div`
  color: var(--gray7);
  font-size: 12px;
  line-height: 40px;
`

interface CreateTimeProps {
  time: number
  style?: CSSProperties
}

function CreateTime({ time, style }: CreateTimeProps): ReactElement {
  const _time = dayjs(time * 1000).format('YYYY-MM-DD HH:mm:ss')
  return <Container style={style}>{_time}</Container>
}

export default CreateTime
