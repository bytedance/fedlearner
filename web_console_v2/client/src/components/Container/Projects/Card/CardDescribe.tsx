import React, { ReactElement } from 'react'
import styled from 'styled-components'

interface CardDescribeProps {
  describe: string
  children: React.ReactNode
}

const Container = styled.div`
  padding: 10px 16px;
  flex: 1;
  .describe{
    font-size: 13px;
    line-height: 22px;
    color: var(--gray7);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
`

function CardDescribe(props: CardDescribeProps):ReactElement {
  return (
    <Container>
      <span className="describe">{props.describe}</span>
      {props.children}
    </Container>
  )
}

export default CardDescribe
