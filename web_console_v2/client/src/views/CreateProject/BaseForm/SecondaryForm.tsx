import React, { ReactElement } from 'react'
import { useToggle } from 'react-use'
import styled from 'styled-components'
import classNames from 'classnames'

const Container = styled.div`
  background-color: white;
  padding: 24px;
  margin-top: 14px;
  border-radius: 4px;
`

const Header = styled.div`
  font-weight: 600;
  font-size: 16px;
  line-height: 24px;
  color: var(--gray10);
`

const Body = styled.div`
  width: 500px;
  margin-top: 32px;
`

interface Props {
  children: React.ReactNode
  title?: string
  suffix?: React.ReactNode
}

function SecondaryForm({ title, children, suffix }: Props): ReactElement {
  return (
    <Container>
      {title ? <Header>{title}</Header> : null}
      <Body>{children}</Body>
      {suffix ?? null}
    </Container>
  )
}

export default SecondaryForm
