import React, { FC } from 'react';
import styled from 'styled-components';
import { userInfoQuery } from 'stores/user';
import avatar from 'assets/images/avatar.jpg';
import { useRecoilQuery } from 'hooks/recoil';
import { MixinCommonTransition, MixinSquare } from 'styles/mixins';
import { message, Popover, Button } from 'antd';
import GridRow from 'components/_base/GridRow';
import { Settings } from 'components/IconPark';
import { Redirect, useHistory } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { useResetRecoilState } from 'recoil';
import { ErrorCodes } from 'typings/app';
import i18n from 'i18n';
import { FedUserInfo } from 'typings/auth';
import UserRoleBadge from 'components/UserRoleBadge';

const Container = styled.div`
  ${MixinCommonTransition()}
  display: flex;
  align-items: center;
  padding: 2px;
  cursor: pointer;
  border-radius: 50%;

  &:hover {
    background: var(--backgroundColorGray);
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
  background-color: var(--backgroundColorGray);
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
const ButtonRow = styled(GridRow)`
  height: 40px;
  margin-bottom: 10px;
  padding: 0 20px;
  cursor: pointer;

  &:hover {
    background-color: var(--gray1);
  }
`;
const LogoutButton = styled(Button)`
  width: 100%;
  margin-top: 5px;
`;

export const ACCOUNT_CHANNELS = {
  click_settings: 'click_settings',
};

const AccountPopover: FC = () => {
  const history = useHistory();
  const { t } = useTranslation();
  const resetUserInfo = useResetRecoilState(userInfoQuery);

  return (
    <div>
      <ButtonRow gap="5" onClick={onSettingClick}>
        <Settings />
        {t('app.system_settings')}
      </ButtonRow>
      <LogoutButton size="large" onClick={onLogoutClick}>
        {t('app.logout')}
      </LogoutButton>
    </div>
  );

  async function onLogoutClick() {
    try {
      // logout api is now unavailable, only fe remove the user storage.
      // await logout();
      store.remove(LOCAL_STORAGE_KEYS.current_user);
      resetUserInfo();
      history.push('/login');
    } catch (error) {
      message.error(error.message);
    }
  }

  function onSettingClick() {
    history.push('/settings');
  }
};
const Username: FC<{ userInfo: FedUserInfo }> = ({ userInfo }) => {
  return (
    <UsernameRow gap="10">
      <h3 className="username">{userInfo?.name}</h3>
      <UserRoleBadge role={userInfo.role} />
    </UsernameRow>
  );
};

function HeaderAccount() {
  const { isLoading, data: userInfo, error } = useRecoilQuery(userInfoQuery);

  if (error && error.code === ErrorCodes.TokenExpired) {
    message.info(i18n.t('error.token_expired'));
    return <Redirect to="/login" />;
  }

  if (isLoading) {
    return <EmptyAvatar />;
  }

  if (Boolean(error)) {
    return null;
  }

  return (
    <Popover
      content={<AccountPopover />}
      title={<Username userInfo={userInfo} />}
      placement="bottomLeft"
    >
      <Container>
        <Avatar src={avatar} alt="avatar" className="user-avatar" />
      </Container>
    </Popover>
  );
}

export default HeaderAccount;
