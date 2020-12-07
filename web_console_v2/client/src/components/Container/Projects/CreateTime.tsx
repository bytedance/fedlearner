import React, { ReactElement } from 'react'
import styled from "styled-components"
import dayjs from 'dayjs'

const Container = styled.div`
  color: var(--gray7);
  font-size: 12px;
  line-height: 40px;
`

interface CreateTimeProps {
  time: number
}

function CreateTime(props: CreateTimeProps): ReactElement {
  const time = dayjs(props.time).format('YYYY-MM-DD HH:mm:ss')
  return (
    <Container>
      { time }
    </Container>
  )
}

export default CreateTime
