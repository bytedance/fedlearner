import React from 'react'
import styled from 'styled-components'
import { userInfoQuery } from 'stores/user'

import avatar from 'assets/images/fake-avatar.jpg'
import { useRecoilQuery } from 'hooks/recoil'

const Container = styled.div`
  display: flex;
  align-items: center;

  > .user-avatar {
    width: 30px;
    height: 30px;
    border-radius: 50%;
  }

  > .username {
    margin-left: 5px;
  }
`

function HeaderAccount() {
  const { isLoading, data: userInfo, error } = useRecoilQuery(userInfoQuery)

  if (isLoading) {
    return <div>Loading....</div>
  }

  if (Boolean(error)) {
    return <div>Load userinfo error!</div>
  }

  return (
    <Container>
      <img src={avatar} alt="avatar" className="user-avatar" />

      <span className="username">{userInfo?.name}</span>
    </Container>
  )
}

export default HeaderAccount
