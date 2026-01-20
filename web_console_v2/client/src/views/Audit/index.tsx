import React, { FC } from 'react';
import ErrorBoundary from 'components/ErrorBoundary';
import { Route } from 'react-router-dom';
import EventList from './EventList';

const Audit: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/audit/event" exact component={EventList} />
    </ErrorBoundary>
  );
};

export default Audit;
