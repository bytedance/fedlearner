import React, { FC } from 'react';
import { Route } from 'react-router-dom';
import styled from 'styled-components';
import PodLogs from './PodLogs';

const Container = styled.main`
  padding: 30px;
  height: 100vh;
  background-color: #292238;
  overflow-y: auto;
`;
const LogsArea = styled.pre`
  width: 100%;
  color: #fefefe;
  text-shadow: 0 0 2px #001716, 0 0 3px #03edf975, 0 0 5px #03edf975, 0 0 8px #03edf975;
`;

const LogsViewer: FC = () => {
  return (
    <Container>
      <LogsArea>
        <Route path="/logs/pod/:jobid/:podname" exact component={PodLogs} />
      </LogsArea>
    </Container>
  );
};

export default LogsViewer;
