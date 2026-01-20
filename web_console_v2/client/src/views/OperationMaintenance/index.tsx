import React from 'react';
import { Route } from 'react-router-dom';
import OperationList from './OperationList';

function OperationMaintenancePage() {
  return (
    <>
      <Route path="/operation" exact component={OperationList} />
    </>
  );
}

export default OperationMaintenancePage;
