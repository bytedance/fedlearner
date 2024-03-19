import React, { FC } from 'react';
import { Route } from 'react-router-dom';

import ErrorBoundary from 'components/ErrorBoundary';

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
