import React from 'react'
import styled from 'styled-components'
import { StyledComponetProps } from 'typings/component'

const Container = styled.footer`
  text-align: center;
  background-color: #f0f0f0;
`

function Footer({ className }: StyledComponetProps) {
  return <Container className={className}>@fl</Container>
}

export default Footer
