import React from 'react';

import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Route } from 'react-router-dom';
import TemplateCreate from './TemplateCreate';

function WorkflowsPage() {
  return (
    <ErrorBoundary>
      <Route path="/workflows" exact component={TemplateCreate} />
      <Route path="/workflow-templates" exact component={TemplateList} />
      <Route path="/workflow-templates/create/:step" component={CreateTemplate} />
    </ErrorBoundary>
  );
}

export default WorkflowsPage;
