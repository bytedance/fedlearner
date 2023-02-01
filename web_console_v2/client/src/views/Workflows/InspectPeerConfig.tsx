import React, { FC } from 'react';
import styled from './InspectPeerConfig.module.less';
import { Modal, Tabs } from '@arco-design/web-react';
import { ModalProps } from '@arco-design/web-react/es/Modal/modal';
import { useTranslation } from 'react-i18next';
import { WorkflowConfig } from 'typings/workflow';
import PropertyList from 'components/PropertyList';
import NoResult from 'components/NoResult';

const InspectPeerConfig: FC<
  ModalProps & { toggleVisible: Function; config: WorkflowConfig | null }
> = ({ config, toggleVisible, ...props }) => {
  const { t } = useTranslation();

  if (!config) return null;

  const jobs = config.job_definitions ?? [];

  const hasJob = Boolean(jobs.length);

  return (
    <Modal
      className={styled.inspect_modal}
      {...props}
      onOk={closeModal}
      okText={t('close')}
      cancelButtonProps={{
        style: { display: 'none' },
      }}
      onCancel={closeModal}
    >
      <h2 className={styled.modal_header}>{t('workflow.peer_config')}</h2>

      {config && hasJob && (
        <Tabs type="card" defaultActiveTab={jobs[0].name}>
          {jobs.map((item) => {
            return (
              <Tabs.TabPane title={item.name} key={item.name}>
                <PropertyList
                  cols={1}
                  labelWidth={100}
                  properties={item.variables.map((vari) => {
                    return {
                      label: vari.name,
                      value:
                        vari.value && typeof vari.value === 'object'
                          ? JSON.stringify(vari.value)
                          : vari.value,
                    };
                  })}
                />
              </Tabs.TabPane>
            );
          })}
        </Tabs>
      )}

      {!hasJob && (
        <div className={styled.no_job}>
          <NoResult text="对侧暂无任务" />
        </div>
      )}
    </Modal>
  );

  function closeModal() {
    toggleVisible(false);
  }
};

export default InspectPeerConfig;
