import React, { FC } from 'react';
import { useHistory } from 'react-router-dom';

import { createNewUser } from 'services/user';

import { Message } from '@arco-design/web-react';
import UserForm from '../UserForm';

import { FedRoles, FedUserInfo } from 'typings/auth';

const UserCreate: FC = () => {
  const history = useHistory();

  return <UserForm isEdit={false} onSubmit={onSubmit} initialValues={{ role: FedRoles.User }} />;

  async function onSubmit(data: any) {
    await createNewUser(data as FedUserInfo)
      .then(() => {
        history.push('/users');
      })
      .catch((error) => {
        const { code, message } = error;

        let displayMessage = message;

        // Get username from error.message
        // e.g. user username1 already exists => username1
        const regx = /user (.+) already exists/;
        const result = String(message).match(regx);

        if (code === 409 && result && result[1]) {
          displayMessage = `用户名：${result[1]} 已存在或者被删除`;
        }

        Message.error(displayMessage);
      });
  }
};

export default UserCreate;
