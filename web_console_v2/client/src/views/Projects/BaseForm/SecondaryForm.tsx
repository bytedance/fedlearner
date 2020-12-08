import React, { ReactElement } from 'react'
import { useToggle } from 'react-use'
import styled from 'styled-components'
import classNames from 'classnames'

const Container = styled.div``

const Header = styled.div``

const Body = styled.div`
  &.hide {
    display: none;
  }
`

interface Props {
  children: React.ReactNode
  title: string
  folded?: boolean
}

function SecondaryForm({ title, children, folded }: Props): ReactElement {
  const [isFolded, toggleFold] = useToggle(folded ?? false)
  return (
    <Container>
      <Header>
        {title}
        {folded ? <div onClick={toggleFold}>收起</div> : null}
      </Header>
      <Body className={classNames({ hide: isFolded })}>{children}</Body>
    </Container>
  )
}

export default SecondaryForm
