import React, { FC } from 'react';
import { Route } from 'react-router-dom';
import styled from 'styled-components';
import PodLogs from './PodLogs';
import JobLogs from './JobLogs';
import JobEvents from './JobEvents';

const Container = styled.main`
  padding-left: 10px;
  height: 100vh;
  background-color: #292238;
`;
const LogsViewer: FC = () => {
  return (
    <Container>
      <Route path="/logs/pod/:jobId/:podname" exact component={PodLogs} />
      <Route path="/logs/job/:jobId" exact component={JobLogs} />
      <Route path="/logs/job/events/:side/:jobIdOrName" exact component={JobEvents} />
    </Container>
  );
};

export default LogsViewer;
