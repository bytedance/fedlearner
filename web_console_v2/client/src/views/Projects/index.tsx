import React, { FC } from 'react';
import ErrorBoundary from 'components/ErrorBoundary';
import { Redirect, Route } from 'react-router-dom';
import ProjectList from './ProjectList';
import CreateProject from './CreateProject';
import EditProject from './EditProject';
import ProjectDetail from './ProjectDetail';
import ReceiverProject from './ReceiverProject';

const ProjectsPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/projects" exact component={ProjectList} />
      <Route
        path="/projects/create"
        exact
        render={() => <Redirect to="/projects/create/config" />}
      />
      <Route path="/projects/create/:step" exact component={CreateProject} />
      <Route path="/projects/edit/:id" exact component={EditProject} />
      <Route path="/projects/:projectListType/detail/:id" exact component={ProjectDetail} />
      <Route path="/projects/receiver/:id" exact component={ReceiverProject} />
    </ErrorBoundary>
  );
};

export default ProjectsPage;
