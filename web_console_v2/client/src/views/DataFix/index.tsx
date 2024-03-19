import React from 'react';
import { Route } from 'react-router-dom';
import DataFixForm from './DataFixForm';

function DataFix() {
  return (
    <>
      <Route path="/data_fix" exact component={DataFixForm} />
    </>
  );
}

export default DataFix;
