import React, { ReactElement } from 'react'
import styled from 'styled-components'
import dayjs from 'dayjs'

const Container = styled.div`
  color: var(--gray7);
  font-size: 12px;
  line-height: 40px;
`

interface CreateTimeProps {
  time: number
}

function CreateTime({ time }: CreateTimeProps): ReactElement {
  const _time = dayjs(time).format('YYYY-MM-DD HH:mm:ss')
  return <Container>{_time}</Container>
}

export default CreateTime
