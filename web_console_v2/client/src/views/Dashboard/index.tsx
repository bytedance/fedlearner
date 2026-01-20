import React from 'react';
import { Route } from 'react-router-dom';
import DashboardDetail from './DashboardDetail';

function Dashboard() {
  return (
    <>
      <Route path="/dashboard" exact component={DashboardDetail} />
      <Route path="/dashboard/:uuid" exact component={DashboardDetail} />
    </>
  );
}

export default Dashboard;
