import React, { FC } from 'react';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import { Route } from 'react-router-dom';
import ProjectList from './ProjectList';
import CreateProject from './CreateProject';
import EditProject from './EditProject';

const ProjectsPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/projects" exact component={ProjectList} />
      <Route path="/projects/create" exact component={CreateProject} />
      <Route path="/projects/edit" exact component={EditProject} />
    </ErrorBoundary>
  );
};

export default ProjectsPage;
