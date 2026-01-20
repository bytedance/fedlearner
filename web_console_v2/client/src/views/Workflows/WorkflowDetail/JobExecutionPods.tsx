import React, { FC } from 'react';
import styled from './JobExecutionPods.module.less';
import { Table, Button } from '@arco-design/web-react';
import { JobExecutionDetalis, Pod, PodState } from 'typings/job';
import i18n from 'i18n';
import StateIndicator from 'components/StateIndicator';
import { useTranslation } from 'react-i18next';
import ClickToCopy from 'components/ClickToCopy';
import { getPodState } from '../shared';

type Props = {
  job?: JobExecutionDetalis;
  isPeerSide: boolean;
  loading: boolean;
};

const JobExecutionPods: FC<Props> = ({ job, isPeerSide, loading }) => {
  const { t } = useTranslation();

  let data = job?.pods;
  if (!Array.isArray(data)) {
    data = [];
  }
  const tablecolumns = [
    {
      title: i18n.t('workflow.col_pod_name'),
      dataIndex: 'name',
      key: 'name',
      width: 380,
      render: (val: string) => {
        return <ClickToCopy text={val}>{val}</ClickToCopy>;
      },
    },
    !isPeerSide &&
      ({
        title: i18n.t('workflow.col_pod_ip'),
        dataIndex: 'pod_ip',
        key: 'pod_ip',
        sorter(a: Pod, b: Pod) {
          return a.pod_ip.localeCompare(b.pod_ip);
        },
      } as any),
    {
      title: i18n.t('workflow.col_worker_status'),
      dataIndex: 'state',
      key: 'state',
      sorter(a: Pod, b: Pod) {
        return a.state.localeCompare(b.state);
      },
      render: (_: PodState, record: Pod) => {
        return <StateIndicator {...getPodState(record)} />;
      },
    },
    {
      title: i18n.t('workflow.col_worker_type'),
      dataIndex: 'pod_type',
      key: 'pod_type',
      sorter(a: Pod, b: Pod) {
        return a.pod_type.localeCompare(b.pod_type);
      },
    },
  ].filter(Boolean);

  if (!isPeerSide) {
    tablecolumns.push({
      title: i18n.t('workflow.col_actions'),
      dataIndex: 'actions',
      key: 'actions',
      width: 160,
      render: (_: any, record: Pod) => {
        return (
          <div style={{ marginLeft: '-13px' }}>
            <Button type="text" size="small" onClick={() => goInspectLogs(record)}>
              {i18n.t('workflow.btn_inspect_logs')}
            </Button>
          </div>
        );
      },
    } as any);
  }

  return (
    <div className={styled.container}>
      <h3>{t('workflow.label_pod_list')}</h3>
      <Table loading={loading} data={data || []} columns={tablecolumns} size="small" />
    </div>
  );

  function goInspectLogs(pod: Pod) {
    window.open(`/v2/logs/pod/${job?.id}/${pod.name}`, '_blank noopener');
  }
};

export default JobExecutionPods;
