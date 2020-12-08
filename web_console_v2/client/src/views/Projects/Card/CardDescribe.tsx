import React, { ReactElement } from 'react'
import styled from 'styled-components'

interface CardDescribeProps {
  describe: string
  children: React.ReactNode
}

const Container = styled.div`
  padding: 10px 16px;
  flex: 1;
  .describe {
    font-size: 13px;
    line-height: 22px;
    color: var(--gray7);
  }
`

function CardDescribe({ describe, children }: CardDescribeProps): ReactElement {
  return (
    <Container>
      <span className="describe ellipsis">{describe}</span>
      {children}
    </Container>
  )
}

export default CardDescribe
