import React from 'react';

import ErrorBoundary from 'components/ErrorBoundary';
import { Route } from 'react-router-dom';
import TemplateList from './TemplateList';
import CreateTemplate from './CreateTemplate';
import EditTemplate from './EditTemplate';
import TemplateDetail from './TemplateDetail';
import routesMap from './routes';

function WorkflowsPage() {
  return (
    <ErrorBoundary>
      <Route path="/workflow-center/workflow-templates" exact component={TemplateList} />
      <Route path="/workflow-center/workflow-templates/upload" exact component={TemplateList} />
      <Route path="/workflow-center/workflow-templates/create/:step" component={CreateTemplate} />
      <Route
        path="/workflow-center/workflow-templates/edit/:step/:id/:revision_id?"
        component={EditTemplate}
      />
      <Route path={routesMap.WorkflowTemplateDetail} exact component={TemplateDetail} />
    </ErrorBoundary>
  );
}

export default WorkflowsPage;
