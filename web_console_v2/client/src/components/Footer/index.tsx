import React from 'react'
import styled from 'styled-components'

const Container = styled.footer`
  height: 100px;
  line-height: 100px;
  text-align: center;
  background-color: #f0f0f0;
`

function Footer() {
  return <Container>@bytedance</Container>
}

export default Footer
