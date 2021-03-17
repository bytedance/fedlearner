import React from 'react';

import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Route } from 'react-router-dom';
import TemplateList from './TemplateList';
import CreateTemplate from './CreateTemplate';
import EditTemplate from './EditTemplate';

function WorkflowsPage() {
  return (
    <ErrorBoundary>
      <Route path="/workflow-templates" exact component={TemplateList} />
      <Route path="/workflow-templates/create/:step" component={CreateTemplate} />
      <Route path="/workflow-templates/edit/:step/:id" component={EditTemplate} />
    </ErrorBoundary>
  );
}

export default WorkflowsPage;
