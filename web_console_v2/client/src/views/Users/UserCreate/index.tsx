import { message } from 'antd';
import React, { FC } from 'react';
import { useHistory } from 'react-router-dom';
import { createNewUser } from 'services/user';
import { FedRoles, FedUserInfo } from 'typings/auth';
import UserForm from '../UserForm';

const UserCreate: FC = () => {
  const history = useHistory();

  return <UserForm isEdit={false} onSubmit={onSubmit} initialValues={{ role: FedRoles.User }} />;

  async function onSubmit(data: any) {
    await createNewUser(data as FedUserInfo)
      .then(() => {
        history.push('/users');
      })
      .catch((e) => {
        message.error(e.toString());
      });
  }
};

export default UserCreate;
