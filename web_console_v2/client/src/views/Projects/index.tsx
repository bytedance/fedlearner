import React, { FC } from 'react'
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary'
import { Route } from 'react-router-dom'
import ProjectList from './ProjectList'

const ProjectsPage: FC = () => {
  return (
    <ErrorBoundary>
      <Route path="/projects" exact component={ProjectList} />
    </ErrorBoundary>
  )
}

export default ProjectsPage
