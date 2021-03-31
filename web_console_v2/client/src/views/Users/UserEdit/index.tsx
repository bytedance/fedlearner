import { message } from 'antd';
import React, { FC } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from 'react-query';
import { useHistory, useParams } from 'react-router-dom';
import { fetchUserInfo, updateUser } from 'services/user';
import { FedUserInfo } from 'typings/auth';
import UserForm from '../UserForm';

const UserEdit: FC = () => {
  const { t } = useTranslation();
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
        message.success(t('users.message_modify_success'));
        history.push('/users');
      })
      .catch((e) => {
        message.error(e.toString());
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
