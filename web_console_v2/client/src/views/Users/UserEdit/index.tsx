import React, { FC } from 'react';
import { useHistory, useParams } from 'react-router-dom';
import { useQuery } from 'react-query';

import { fetchUserInfo, updateUser } from 'services/user';

import { Message } from '@arco-design/web-react';
import UserForm from '../UserForm';

import { FedUserInfo } from 'typings/auth';

const UserEdit: FC = () => {
  const { id } = useParams<{ id: string }>();

  const currUserQuery = useQuery(['getCurrUserInfo', id], () => fetchUserInfo(id), {
    cacheTime: 1,
    refetchOnWindowFocus: false,
  });
  const history = useHistory();

  const initialValues = { ...currUserQuery.data?.data };

  return (
    <>
      {currUserQuery.data && !currUserQuery.isFetching && (
        <UserForm isEdit={true} onSubmit={onSubmit} initialValues={initialValues} />
      )}
    </>
  );

  async function onSubmit(data: Partial<FedUserInfo>) {
    const payload = getChangedValues(data);

    await updateUser(initialValues.id!, payload)
      .then(() => {
        Message.success('修改成功');
        history.push('/users');
      })
      .catch((e) => {
        Message.error(e.toString());
      });
  }

  function getChangedValues(data: Partial<FedUserInfo>) {
    return Object.entries(data).reduce((ret, [key, value]) => {
      if (value !== initialValues[key as keyof typeof initialValues]) {
        ret[key] = value;
      }

      return ret;
    }, {} as any);
  }
};

export default UserEdit;
