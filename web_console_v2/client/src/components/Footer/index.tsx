import React from 'react'
import styled from 'styled-components'

const Container = styled.footer`
  text-align: center;
  background-color: #f0f0f0;
`

function Footer({ className }: StyledComponetProps) {
  return <Container className={className}>@bytedance</Container>
}

export default Footer
