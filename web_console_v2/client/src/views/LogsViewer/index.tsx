import React, { FC } from 'react';
import { Route } from 'react-router-dom';
import PodLogs from './PodLogs';
import JobLogs from './JobLogs';
import JobEvents from './JobEvents';
import SystemLogs from './SystemLogs';
import ModelServingInstanceLogs from './ModelServingInstanceLogs';

import styles from './index.module.less';

const LogsViewer: FC = () => {
  return (
    <main className={styles.container}>
      <Route path="/logs/job/:jobId" exact component={JobLogs} />
      <Route path="/logs/pod/:jobId/:podname/:startTime?" exact component={PodLogs} />
      <Route path="/logs/job/events/:jobIdOrK8sName" exact component={JobEvents} />
      <Route path="/logs/job/events/:side/:jobIdOrK8sName/:uuid" exact component={JobEvents} />
      <Route path="/logs/system" exact component={SystemLogs} />
      <Route
        path="/logs/model-serving/:modelServingId/:instanceName"
        exact
        component={ModelServingInstanceLogs}
      />
    </main>
  );
};

export default LogsViewer;
