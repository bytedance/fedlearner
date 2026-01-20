import React from 'react';
import { Route } from 'react-router-dom';
import CleanupList from './CleanupList';

function Cleanup() {
  return (
    <>
      <Route path="/cleanup" exact component={CleanupList} />
    </>
  );
}

export default Cleanup;
