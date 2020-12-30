import React, { ReactElement } from 'react'
import styled from 'styled-components'
import question from 'assets/images/question.svg'
import { Tooltip } from 'antd'

const Container = styled.div`
  background-color: white;
  height: 100%;
  width: 100%;
  padding: 22px 24px 0;
  .title-wrapper {
    height: 28px;
    .title {
      line-height: 28px;
      font-size: 20px;
      font-weight: 500;
      color: var(--textColor);
    }
    .title-question {
      display: inline-block;
      margin-top: -6px;
      margin-left: 10px;
      height: 16px;
      width: 16px;
    }
  }
`

interface CardPanelProps {
  title: string
  children?: React.ReactNode
  tip?: string
}

interface CardTitleProps {
  title: string
  tip?: string
}

function CardTitle({ title, tip }: CardTitleProps): ReactElement {
  return (
    <div className="title-wrapper">
      <span className="title">{title}</span>
      <Tooltip title={tip} placement="rightBottom">
        <img src={question} alt="" className="title-question" />
      </Tooltip>
    </div>
  )
}

function CardPanel({ title, children, tip }: CardPanelProps): ReactElement {
  return (
    <Container>
      <CardTitle title={title} tip={tip} />
      {children}
    </Container>
  )
}

export default CardPanel
