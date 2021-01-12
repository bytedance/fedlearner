import React, { FC } from 'react'
import styled from 'styled-components'
import question from 'assets/images/question.svg'
import { Tooltip, Card } from 'antd'
import GridRow from 'components/_base/GridRow'

const Container = styled(Card)`
  > .ant-card-body {
    display: grid;
    grid-auto-flow: row;
    grid-gap: 18px;
    padding: 22px 24px;

    &::before {
      content: none;
    }
  }

  .title-question {
    width: 16px;
    height: 16px;
  }
`
const ListTitle = styled.h2`
  margin-bottom: 0;
  font-size: 20px;
  line-height: 28px;
`

interface Props {
  title: string
  children?: React.ReactNode
  tip?: string
}

const ListPageCard: FC<Props> = ({ title, children, tip }) => {
  return (
    <Container>
      <GridRow gap="10">
        <ListTitle className="title">{title}</ListTitle>

        {tip && (
          <Tooltip title={tip} placement="rightBottom">
            {/* FIXME: icon park */}
            <img src={question} alt="" className="title-question" />
          </Tooltip>
        )}
      </GridRow>

      {children}
    </Container>
  )
}

export default ListPageCard
