import React, { FC } from 'react';
import styled from 'styled-components';
import { userInfoQuery } from 'stores/user';

import avatar from 'assets/images/avatar.svg';
import { useRecoilQuery } from 'hooks/recoil';
import { MixinCircle, MixinCommonTransition, MixinSquare } from 'styles/mixins';
import { message, Popover, Button, Row } from 'antd';
import GridRow from 'components/_base/GridRow';
import LanguageSwitch from './LanguageSwitch';
import { useHistory } from 'react-router-dom';
import { logout } from 'services/user';

const Container = styled.div`
  ${MixinCommonTransition()}
  display: flex;
  align-items: center;
  padding: 4px;
  cursor: pointer;
  border-radius: 50%;

  &:hover {
    background: var(--gray3);
  }
`;

const Avatar = styled.img`
  ${MixinSquare(24)}
  border-radius: 50%;
`;

const EmptyAvatar = styled.div`
  ${MixinSquare(32)}

  border-radius: 50%;
  border: 4px solid transparent;
  background-color: var(--gray3);
  background-clip: content-box;
`;
const UsernameRow = styled(GridRow)`
  width: 300px;
  height: 45px;

  > .username {
    font-size: 16px;
    margin-bottom: 0;
  }
`;
const Role = styled.div`
  display: flex;
  align-items: center;
  padding: 3px;
  padding-right: 10px;
  border-radius: 100px;
  font-size: 12px;
  line-height: 1;
  font-weight: normal;
  background-color: var(--gray3);

  &::before {
    ${MixinCircle(14)}
    content: '';
    display: block;
    margin-right: 4px;
    background-color: var(--darkGray8);
  }
`;
const LanguageRow = styled(Row)`
  height: 40px;
  margin-bottom: 10px;
`;
const LogoutButton = styled(Button)`
  width: 100%;
`;

const AccountPopover: FC = () => {
  const history = useHistory();

  return (
    <div>
      <LanguageRow justify="space-between" align="middle">
        <div>切换语言</div>
        <LanguageSwitch />
      </LanguageRow>
      <LogoutButton onClick={onLogoutClick}>退出登录</LogoutButton>
    </div>
  );

  async function onLogoutClick() {
    try {
      await logout();
      history.push('/login');
    } catch (error) {
      message.error(error.message);
    }
  }
};

const Username: FC<{ name: string }> = ({ name }) => {
  return (
    <UsernameRow gap="10">
      <h3 className="username">{name}</h3>
      <Role>管理员</Role>
    </UsernameRow>
  );
};

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
      <Popover
        content={<AccountPopover />}
        trigger="hover"
        title={<Username name={userInfo?.name || ''} />}
        placement="bottomLeft"
      >
        <Avatar src={avatar} alt="avatar" className="user-avatar" />
      </Popover>
    </Container>
  );
}

export default HeaderAccount;
