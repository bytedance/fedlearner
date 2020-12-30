import React, { ReactElement } from 'react'
import styled from 'styled-components'
import { ReactComponent as TrashCan } from 'assets/images/trash-can.svg'

const Container = styled.div`
  cursor: pointer;
`

interface Props {
  onClick: () => void
}

function TrashCanRemove({ onClick }: Props): ReactElement {
  return (
    <Container onClick={onClick}>
      <TrashCan />
    </Container>
  )
}

export default TrashCanRemove
