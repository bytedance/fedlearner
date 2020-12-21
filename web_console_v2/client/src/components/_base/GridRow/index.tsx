import React, { FunctionComponent } from 'react'
import { convertToUnit } from 'shared/helpers'
import styled from 'styled-components'

const Container = styled.div`
  display: grid;
  grid-gap: ${(props: Props) => convertToUnit(props.gap)};
  justify-content: ${(props: Props) => props.justify || 'start'};
  grid-auto-columns: auto;
  grid-template-rows: auto;
  grid-auto-flow: column;
`

type Props = {
  gap?: number | string
  justify?:
    | 'start'
    | 'end'
    | 'center'
    | 'stretch'
    | 'space-between'
    | 'space-around'
    | 'space-evenly'
}

const GridRow: FunctionComponent<Props> = (props) => {
  return (
    <Container role="grid" {...props}>
      {props.children}
    </Container>
  )
}

export default GridRow
