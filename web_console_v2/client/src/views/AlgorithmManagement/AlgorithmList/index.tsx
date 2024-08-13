import React, { FC } from 'react';
import { useParams, useHistory } from 'react-router';

import { AlgorithmManagementTabType } from 'typings/modelCenter';

import { Tabs } from '@arco-design/web-react';
import SharedPageLayout, { RemovePadding } from 'components/SharedPageLayout';
import MyAlgorithmTab from './MyAlgorithmTab';
import BuiltInAlgorithmTab from './BuiltInAlgorithmTab';
import ParticipantAlgorithmTab from './ParticipantAlgorithmTab';
import { Redirect, Route } from 'react-router';
import styled from './index.module.less';

const AlgorithmManagementList: FC = () => {
  const history = useHistory();

  const { tabType } = useParams<{ tabType: AlgorithmManagementTabType }>();
  if (!tabType) {
    return <Redirect to={`/algorithm-management/${AlgorithmManagementTabType.MY}`} />;
  }
  return (
    <SharedPageLayout title="算法仓库">
      <RemovePadding style={{ height: 46 }}>
        <Tabs className={styled.algorithm_tab} defaultActiveTab={tabType} onChange={onTabChange}>
          <Tabs.TabPane title="我的算法" key={AlgorithmManagementTabType.MY} />
          <Tabs.TabPane title="预置算法" key={AlgorithmManagementTabType.BUILT_IN} />
          <Tabs.TabPane title="合作伙伴算法" key={AlgorithmManagementTabType.PARTICIPANT} />
        </Tabs>
      </RemovePadding>
      <Route
        path={`/algorithm-management/${AlgorithmManagementTabType.MY}`}
        exact
        render={(props) => {
          return <MyAlgorithmTab />;
        }}
      />
      <Route
        path={`/algorithm-management/${AlgorithmManagementTabType.BUILT_IN}`}
        exact
        render={(props) => {
          return <BuiltInAlgorithmTab />;
        }}
      />
      <Route
        path={`/algorithm-management/${AlgorithmManagementTabType.PARTICIPANT}`}
        exact
        render={(props) => {
          return <ParticipantAlgorithmTab />;
        }}
      />
    </SharedPageLayout>
  );

  function onTabChange(val: string) {
    history.replace(`/algorithm-management/${val}`);
  }
};

export default AlgorithmManagementList;
