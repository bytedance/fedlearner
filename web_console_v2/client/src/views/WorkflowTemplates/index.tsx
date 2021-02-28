import React from 'react';

import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Route } from 'react-router-dom';
import TemplateCreate from './TemplateCreate';

function WorkflowsPage() {
  return (
    <ErrorBoundary>
      <Route path="/workflows" exact component={TemplateCreate} />
    </ErrorBoundary>
  );
}

export default WorkflowsPage;
