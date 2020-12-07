import React, { ReactElement } from 'react'
import styled from 'styled-components'
import question from 'assets/images/question.svg'
import { Tooltip } from 'antd';

const Container = styled.div`
  background-color: white;
  height: 100%;
  width: 100%;
  padding: 22px 24px 0;
  .title-wrapper {
    height: 28px;
    .title{
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
}

interface CardTitleProps {
  title: string
}

function CardTitle(props: CardTitleProps): ReactElement {
  const tip = '提供项目的新增和管理功能，支持对项目进行新增、编辑、查询、删除功能，可查看一个项目下的联邦工作流任务列表、模型列表、API列表，一个项目下可创建多个联邦工作流任务。'
  return (
    <div className="title-wrapper">
      <span className="title" >{props.title}</span>
      <Tooltip title={tip} placement="rightBottom">
        <img src={question} alt="" className="title-question"/>
      </Tooltip>
    </div>
  )
}

function CardPanel(props: CardPanelProps): ReactElement {
  return (
    <Container>
      <CardTitle title={props.title} />
      {props.children}
    </Container>
  )
}

export default CardPanel
