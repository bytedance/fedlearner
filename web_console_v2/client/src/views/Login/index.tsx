import React from 'react'
import styled from 'styled-components'

const Layout = styled.main`
  display: grid;
  grid-template-areas: 'left right';
  grid-template-columns: repeat(1fr, 2);
  min-width: 500px;
  height: 100vh;
  min-height: 500px;
  background-color: #fff;

  @media screen and (max-width: 1000px) {
    grid-template-columns: 1fr 500px;
  }
`

const Block = styled.section`
  height: 100%;
`

const Left = styled(Block)`
  background-color: #111;

  @media screen and (max-width: 500px) {
    display: none;
  }
`

const Right = styled(Block)`
  background-color: white;
`

function Login() {
  return (
    <Layout>
      <Left />
      <Right />
    </Layout>
  )
}

export default Login
