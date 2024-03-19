import ErrorBoundary from 'components/ErrorBoundary';
import React, { ForwardRefRenderFunction } from 'react';
import styled from './GlobalConfigDrawer.module.less';
import { Drawer, Grid, Button, Tag } from '@arco-design/web-react';
import { DrawerProps } from '@arco-design/web-react/es/Drawer';
import { NodeData } from 'components/WorkflowJobsCanvas/types';
import { useTranslation } from 'react-i18next';
import { IconClose } from '@arco-design/web-react/icon';
import GridRow from 'components/_base/GridRow';
import PropertyList from 'components/PropertyList';
import { WorkflowExecutionDetails } from 'typings/workflow';
import { Link } from 'react-router-dom';
import WhichProject from 'components/WhichProject';
import { useStoreActions } from 'react-flow-renderer';
import { VariablePermissionLegend } from 'components/VariblePermission';

const Row = Grid.Row;

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
      label: t('workflow.label_template_group'),
      value: workflow?.config?.group_alias || (
        <Link to={`/workflow-center/workflows/accept/basic/${workflow?.id}`}>
          {t('workflow.job_node_pending')}
        </Link>
      ),
    },
    {
      label: t('workflow.label_project'),
      // TODO: peerWorkflow no project id
      value: <WhichProject id={workflow?.project_id} />,
    },
    // Display workflow global variables
    ...(workflow?.config?.variables || []).map((item) => ({
      label: item.name,
      value: item.value,
      accessMode: item.access_mode,
    })),
  ];

  return (
    <ErrorBoundary>
      <Drawer
        className={styled.container}
        mask={false}
        width="980px"
        onCancel={closeDrawer}
        headerStyle={{ display: 'none' }}
        wrapClassName="#app-content"
        footer={null}
        {...props}
      >
        <Row className={styled.drawer_header} align="center" justify="space-between">
          <Row align="center">
            <h3 className={styled.drawer_title}>{job.name}</h3>

            {isPeerSide ? (
              <Tag color="orange">{t('workflow.peer_config')}</Tag>
            ) : (
              <Tag color="cyan">{t('workflow.our_config')}</Tag>
            )}
          </Row>
          <GridRow gap="10">
            <Button size="small" icon={<IconClose />} onClick={closeDrawer} />
          </GridRow>
        </Row>
        <VariablePermissionLegend desc={true} prefix="对侧" style={{ marginTop: 15 }} />
        <PropertyList initialVisibleRows={3} cols={2} properties={workflowProps} labelWidth={90} />
      </Drawer>
    </ErrorBoundary>
  );

  function closeDrawer() {
    setSelectedElements([]);
    toggleVisible && toggleVisible(false);
  }
};

export default GlobalConfigDrawer;
