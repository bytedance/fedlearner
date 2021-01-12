import React from 'react';
import styled from 'styled-components';
import { userInfoQuery } from 'stores/user';

import avatar from 'assets/images/fake-avatar.jpg';
import { useRecoilQuery } from 'hooks/recoil';
import { MixinSquare } from 'styles/mixins';
import { message } from 'antd';

const Container = styled.div`
  display: flex;
  align-items: center;

  > .user-avatar {
    ${MixinSquare(30)}

    border-radius: 50%;
  }

  > .username {
    display: none;
    margin-left: 5px;
  }
`;

const EmptyAvatar = styled.div`
  ${MixinSquare(30)}

  border-radius: 50%;
  background-color: var(--gray5);
`;

function HeaderAccount() {
  const { isLoading, data: userInfo, error } = useRecoilQuery(userInfoQuery);

  if (isLoading) {
    return <EmptyAvatar />;
  }

  if (Boolean(error)) {
    message.error(error?.message);
    return null;
  }

  return (
    <Container>
      <img src={avatar} alt="avatar" className="user-avatar" />

      <span className="username">{userInfo?.name}</span>
    </Container>
  );
}

export default HeaderAccount;
