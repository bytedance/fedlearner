import React, { FC } from 'react';
import ErrorBoundary from 'components/ErrorBoundary';
import { Route } from 'react-router-dom';
import ImageVersion from './ImageVersion/proxy';
import SystemVariables from './SystemVariables';

const SettingsPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/settings/image" exact component={ImageVersion as FC} />
      <Route path="/settings/variables" exact component={SystemVariables} />
    </ErrorBoundary>
  );
};

export default SettingsPage;
