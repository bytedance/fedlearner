import React, { FC, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams, useHistory } from 'react-router';

import { WorkflowType } from 'typings/workflow';

import { Tabs } from '@arco-design/web-react';
import SharedPageLayout, { RemovePadding } from 'components/SharedPageLayout';
import List from './List';
import styled from './index.module.less';

const WorkflowList: FC = () => {
  const { t } = useTranslation();
  const history = useHistory();
  const { tabType } = useParams<{ tabType: WorkflowType }>();

  const [activeKey, setActiveKey] = useState<WorkflowType>(tabType || WorkflowType.MY);

  return (
    <SharedPageLayout title={t('menu.label_workflow')}>
      <RemovePadding style={{ height: 46 }}>
        <Tabs className={styled.workflow_tabs} defaultActiveTab={activeKey} onChange={onTabChange}>
          <Tabs.TabPane title={t('workflow.label_tab_my_workflow')} key={WorkflowType.MY} />
          <Tabs.TabPane title={t('workflow.label_tab_system_workflow')} key={WorkflowType.SYSTEM} />
        </Tabs>
      </RemovePadding>

      {tabType === WorkflowType.MY ? <List type={WorkflowType.MY} /> : null}
      {tabType === WorkflowType.SYSTEM ? <List type={WorkflowType.SYSTEM} /> : null}
    </SharedPageLayout>
  );

  function onTabChange(val: string) {
    setActiveKey(val as WorkflowType);
    history.replace(`/workflow-center/workflows/list/${val}`);
  }
};

export default WorkflowList;
