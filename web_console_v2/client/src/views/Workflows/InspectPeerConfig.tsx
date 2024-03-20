import React, { FC } from 'react';
import styled from 'styled-components';
import { Modal, Tabs, Button } from 'antd';
import { ModalProps } from 'antd/lib/modal/Modal';
import { Close } from 'components/IconPark';
import { useTranslation } from 'react-i18next';
import { WorkflowConfig } from 'typings/workflow';
import PropertyList from 'components/PropertyList';
import { Z_INDEX_GREATER_THAN_HEADER } from 'components/Header';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';
import NoResult from 'components/NoResult';

const InspectModal = styled(Modal)`
  top: 20%;

  .ant-modal-header {
    display: none;
  }
  .ant-modal-body {
    padding: 0;
  }
`;
const ModalHeader = styled.h2`
  padding: 20px;
  padding-bottom: 10px;
  margin-bottom: 0;
  font-size: 16px;
  line-height: 24px;
`;
const JobTabs = styled(Tabs)`
  &.ant-tabs-top > .ant-tabs-nav {
    margin-bottom: 9px;
  }
`;
const NoJob = styled(NoResult)`
  margin: 30px auto;
`;

const InspectPeerConfig: FC<
  ModalProps & { toggleVisible: Function; config: WorkflowConfig | null }
> = ({ config, toggleVisible, ...props }) => {
  const { t } = useTranslation();

  if (!config) return null;

  const jobs = config.job_definitions ?? [];

  const hasJob = Boolean(jobs.length);

  return (
    <ErrorBoundary>
      <InspectModal
        {...props}
        zIndex={Z_INDEX_GREATER_THAN_HEADER}
        onOk={closeModal}
        okText={t('close')}
        cancelButtonProps={{
          style: { display: 'none' },
        }}
        width={455}
        closeIcon={<Button size="small" icon={<Close />} onClick={closeModal} />}
      >
        <ModalHeader>{t('workflow.peer_config')}</ModalHeader>

        {config && hasJob && (
          <JobTabs type="card" defaultActiveKey={jobs[0].name}>
            {jobs.map((item) => {
              return (
                <Tabs.TabPane tab={item.name} key={item.name}>
                  <PropertyList
                    cols={1}
                    labelWidth={100}
                    properties={item.variables.map((vari) => {
                      return {
                        label: vari.name,
                        value: vari.value,
                      };
                    })}
                  />
                </Tabs.TabPane>
              );
            })}
          </JobTabs>
        )}

        {!hasJob && <NoJob text="对侧暂无任务" />}
      </InspectModal>
    </ErrorBoundary>
  );

  function closeModal() {
    toggleVisible(false);
  }
};

export default InspectPeerConfig;
