/* istanbul ignore file */

import React, { FC } from 'react';
import styled from 'styled-components';
import { userInfoQuery, userInfoState } from 'stores/user';
import avatar from 'assets/images/avatar.jpg';
import { useRecoilQuery } from 'hooks/recoil';
import { MixinCommonTransition, MixinSquare } from 'styles/mixins';
import { Message, Popover, Button } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import { Settings, UserGroup, Audit, Common, TeamOutlined } from 'components/IconPark';
import { Redirect, useHistory } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { useResetRecoilState, useRecoilValue } from 'recoil';
import { ErrorCodes } from 'typings/app';
import i18n from 'i18n';
import { FedUserInfo } from 'typings/auth';
import UserRoleBadge from 'components/UserRoleBadge';
import { logout } from 'services/user';
import { useIsAdminRole } from 'hooks/user';
import { appFlag } from 'stores/app';
import { FlagKey } from 'typings/flag';

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
    background-color: rgb(rgb(var(--gray-1)));
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
  const resetUserInfoState = useResetRecoilState(userInfoState);
  const resetUserInfo = useResetRecoilState(userInfoQuery);
  const appFlagValue = useRecoilValue(appFlag);

  const isAdminRole = useIsAdminRole();

  return (
    <div>
      <ButtonRow gap="5" onClick={onMessageClick}>
        <TeamOutlined />
        {t('app.participant')}
      </ButtonRow>
      {isAdminRole && Boolean(appFlagValue[FlagKey.USER_MANAGEMENT_ENABLED]) && (
        <ButtonRow gap="5" onClick={onUserClick}>
          <UserGroup />
          {t('app.user_management')}
        </ButtonRow>
      )}

      {isAdminRole && (
        <ButtonRow gap="5" onClick={onSettingClick}>
          <Settings />
          {t('app.system_settings')}
        </ButtonRow>
      )}

      {isAdminRole && (
        <ButtonRow gap="5" onClick={onAuditClick}>
          <Audit />
          {t('app.audit_log')}
        </ButtonRow>
      )}

      {isAdminRole && (
        <ButtonRow gap="5" onClick={onOperationClick}>
          <Common />
          {t('app.operation_maintenance')}
        </ButtonRow>
      )}

      <LogoutButton size="large" onClick={onLogoutClick}>
        {t('app.logout')}
      </LogoutButton>
    </div>
  );

  async function onLogoutClick() {
    try {
      await logout();
      store.remove(LOCAL_STORAGE_KEYS.current_user);
      store.remove(LOCAL_STORAGE_KEYS.current_project);
      store.remove(LOCAL_STORAGE_KEYS.sso_info);
      resetUserInfoState();
      resetUserInfo();
      history.push('/login');
    } catch (error: any) {
      Message.error(error.message);
    }
  }

  function onUserClick() {
    window.open('/v2/users', '_blank');
  }
  function onSettingClick() {
    window.open('/v2/settings/variables', '_blank');
  }
  function onMessageClick() {
    window.open('/v2/partners', '_blank');
  }
  function onAuditClick() {
    window.open('/v2/audit/event', '_blank');
  }
  function onOperationClick() {
    window.open('/v2/operation', '_blank');
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
    Message.info(i18n.t('error.token_expired'));
    return <Redirect to="/login" />;
  }

  if (isLoading) {
    return <EmptyAvatar />;
  }

  if (Boolean(error)) {
    return null;
  }

  return (
    <Popover content={<AccountPopover />} title={<Username userInfo={userInfo} />} position="bl">
      <Container>
        <Avatar src={avatar} alt="avatar" className="user-avatar" />
      </Container>
    </Popover>
  );
}

export default HeaderAccount;
