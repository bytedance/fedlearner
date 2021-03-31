import React, { FC } from 'react';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Route } from 'react-router-dom';
import UserList from './UserList';
import UserCreate from './UserCreate';
import UserEdit from './UserEdit';

const UsersPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/users" exact component={UserList} />
      <Route path="/users/create" component={UserCreate} />
      <Route path="/users/edit/:id" component={UserEdit} />
    </ErrorBoundary>
  );
};

export default UsersPage;
