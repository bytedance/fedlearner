import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import React, { ForwardRefRenderFunction } from 'react';
import styled from 'styled-components';
import { Drawer, Row, Button, Tag } from 'antd';
import { DrawerProps } from 'antd/lib/drawer';
import { NodeData } from 'components/WorkflowJobsCanvas/types';
import { useTranslation } from 'react-i18next';
import { Close } from 'components/IconPark';
import GridRow from 'components/_base/GridRow';
import PropertyList from 'components/PropertyList';
import { WorkflowExecutionDetails } from 'typings/workflow';
import { Link } from 'react-router-dom';
import WhichProject from 'components/WhichProject';
import { useStoreActions } from 'react-flow-renderer';

const Container = styled(Drawer)`
  top: 60px;

  .ant-drawer-body {
    padding-top: 0;
    padding-bottom: 200px;
  }
`;
const DrawerHeader = styled(Row)`
  position: sticky;
  z-index: 2;
  top: 0;
  margin: 0 -24px 0;
  padding: 20px 16px 20px 24px;
  background-color: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
`;
const DrawerTitle = styled.h3`
  position: relative;
  margin-bottom: 0;
  margin-right: 10px;
`;

interface Props extends DrawerProps {
  isPeerSide?: boolean;
  jobData?: NodeData;
  workflow?: WorkflowExecutionDetails;
  toggleVisible?: Function;
}

export type JobExecutionDetailsExposedRef = {};

const GlobalConfigDrawer: ForwardRefRenderFunction<JobExecutionDetailsExposedRef, Props> = ({
  jobData,
  workflow,
  isPeerSide = false,
  toggleVisible,
  ...props
}) => {
  const { t } = useTranslation();

  const setSelectedElements = useStoreActions((actions) => actions.setSelectedElements);

  if (!jobData || !jobData.raw) {
    return null;
  }

  const job = jobData.raw;

  const workflowProps = [
    {
      label: t('workflow.label_template_name'),
      value: workflow?.config?.group_alias || (
        <Link to={`/workflows/accept/basic/${workflow?.id}`}>{t('workflow.job_node_pending')}</Link>
      ),
    },
    {
      label: t('workflow.label_project'),
      // TODO: peerWorkflow no project id
      value: <WhichProject id={workflow?.project_id || 0} />,
    },
    // Display workflow global variables
    ...(workflow?.config?.variables || []).map((item) => ({
      label: item.name,
      value: item.value,
    })),
  ];

  return (
    <ErrorBoundary>
      <Container
        getContainer="#app-content"
        mask={false}
        width="980px"
        onClose={closeDrawer}
        headerStyle={{ display: 'none' }}
        maskClosable={true}
        {...props}
      >
        <DrawerHeader align="middle" justify="space-between">
          <Row align="middle">
            <DrawerTitle>{job.name}</DrawerTitle>

            {isPeerSide ? (
              <Tag color="orange">{t('workflow.peer_config')}</Tag>
            ) : (
              <Tag color="cyan">{t('workflow.our_config')}</Tag>
            )}
          </Row>
          <GridRow gap="10">
            <Button size="small" icon={<Close />} onClick={closeDrawer} />
          </GridRow>
        </DrawerHeader>
        <PropertyList initialVisibleRows={3} cols={2} properties={workflowProps} labelWidth={90} />
      </Container>
    </ErrorBoundary>
  );

  function closeDrawer() {
    setSelectedElements([]);
    toggleVisible && toggleVisible(false);
  }
};

export default GlobalConfigDrawer;
