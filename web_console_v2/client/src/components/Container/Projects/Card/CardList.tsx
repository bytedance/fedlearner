import React, { ReactElement } from 'react'
import styled from 'styled-components'
import Card from './Card'

const Container = styled.div`
  display: grid;
  grid-template-columns: repeat(3, minmax(272px, 371px));
  column-gap: 24px;
  row-gap: 24px;
  justify-content: space-between;

// 272 * 4 + 24 * 3 + 24 * 2 + 200
  @media screen and (min-width: 1408px) {
    grid-template-columns: repeat(4, minmax(272px, 371px));
  }
`

interface CardListProps {
  projectList: Project[]
}


function CardList(props: CardListProps):ReactElement {
  return (
    <Container>
      {props.projectList.map(item => <Card item={item} key={item.name} />)}
    </Container>
  )
}

export default CardList
