import React, { FC, useMemo, useState } from 'react';
import { Drawer, Table, Button, Tooltip, Progress } from '@arco-design/web-react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PropertyList from 'components/PropertyList';
import { AuthStatus, TicketAuthStatus, TrustedJob, TrustedJobStatus } from 'typings/trustedCenter';
import { useQuery } from 'react-query';
import { fetchTrustedJob } from 'services/trustedCenter';
import { useGetCurrentProjectId } from 'hooks';
import { Pod, PodState } from 'typings/job';
import { fetchJobById } from 'services/workflow';
import { formatTimestamp } from 'shared/date';
import CONSTANTS from 'shared/constants';
import CountTime from 'components/CountTime';
import StateIndicator from 'components/StateIndicator';
import { getPodState } from 'views/Workflows/shared';
import dayjs from 'dayjs';
import { getTicketAuthStatus, getTrustedJobStatus } from 'shared/trustedCenter';
import { DatasetDetailSubTabs } from 'views/Datasets/DatasetDetail';

const AuthStatusMap: Record<AuthStatus, string> = {
  [AuthStatus.AUTHORIZED]: '已授权',
  [AuthStatus.PENDING]: '待授权',
  [AuthStatus.WITHDRAW]: '拒绝授权',
};

export type ExportJobProps = {
  visible: boolean;
  id?: ID;
  jobId?: ID;
  toggleVisible: (val: any) => void;
};

const ExportJobDetailDrawer: FC<ExportJobProps> = ({ visible, toggleVisible, id, jobId }) => {
  const { t } = useTranslation();
  const [trustedJobInfo, setTrustedJobInfo] = useState<TrustedJob>();
  const projectId = useGetCurrentProjectId();
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const trustedJobQuery = useQuery(
    ['fetchTrustedJob', id],
    () => {
      return fetchTrustedJob(projectId!, id!);
    },
    {
      retry: 1,
      refetchOnWindowFocus: false,
      enabled: visible && Boolean(id),
      onSuccess(res) {
        setTrustedJobInfo(res.data);
      },
    },
  );
  const jobsQuery = useQuery(
    ['fetchJobById', jobId],
    () => fetchJobById(jobId).then((res) => res.data.pods),
    {
      enabled: visible && Boolean(jobId),
      retry: 1,
      refetchOnWindowFocus: false,
    },
  );

  const jobList = useMemo(() => {
    if (!jobsQuery?.data) {
      return [];
    }
    const jobs = jobsQuery.data || [];
    return jobs;
  }, [jobsQuery.data]);

  const displayedProps = useMemo(
    () => [
      {
        value: trustedJobInfo?.name,
        label: '导出任务',
      },
      {
        value: trustedJobInfo?.started_at
          ? formatTimestamp(trustedJobInfo?.started_at || 0)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '开始时间',
      },
      {
        value: trustedJobInfo?.finished_at
          ? formatTimestamp(trustedJobInfo?.finished_at || 0)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '结束时间',
      },
      {
        value: trustedJobInfo?.status ? renderRuntime(trustedJobInfo) : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '运行时长',
      },
      {
        value: (() => {
          const data = getTicketAuthStatus(trustedJobInfo!);
          return (
            <>
              <Tooltip
                position="tl"
                content={
                  trustedJobInfo?.ticket_auth_status === TicketAuthStatus.AUTH_PENDING
                    ? renderUnauthParticipantList(trustedJobInfo)
                    : undefined
                }
              >
                <div>{data.text}</div>
              </Tooltip>
              <Progress
                percent={data.percent}
                showText={false}
                style={{ width: 100 }}
                status={data.type}
              />
            </>
          );
        })(),
        label: '审批状态',
      },
      {
        value: (() => {
          return (
            <div className="indicator-with-tip">
              <StateIndicator {...getTrustedJobStatus(trustedJobInfo!)} />
              {trustedJobInfo?.status === TrustedJobStatus.SUCCEEDED && (
                <Link
                  to={`/datasets/processed/detail/${trustedJobInfo.export_dataset_id}/${DatasetDetailSubTabs.DatasetJobDetail}`}
                >
                  查看数据集
                </Link>
              )}
            </div>
          );
        })(),
        label: '任务状态',
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [trustedJobInfo],
  );

  const columns = useMemo(
    () => [
      {
        title: t('trusted_center.col_instance_id'),
        dataIndex: 'name',
        name: 'name',
      },
      {
        dataIndex: 'state',
        title: '状态',
        filters: [
          PodState.SUCCEEDED,
          PodState.RUNNING,
          PodState.FAILED,
          PodState.PENDING,
          PodState.FAILED_AND_FREED,
          PodState.SUCCEEDED_AND_FREED,
          PodState.UNKNOWN,
        ].map((state) => {
          const { text } = getPodState({ state } as Pod);
          return {
            text,
            value: state,
          };
        }),
        onFilter: (state: PodState, record: Pod) => {
          return record?.state === state;
        },
        render(state: any, record: Pod) {
          return <StateIndicator {...getPodState(record)} />;
        },
      },
      {
        title: t('trusted_center.col_instance_start_at'),
        dataIndex: 'created_at',
        name: 'created_at',
        render(_: any, record: any) {
          return record.creation_timestamp
            ? formatTimestamp(record.creation_timestamp)
            : CONSTANTS.EMPTY_PLACEHOLDER;
        },
      },
      {
        title: t('trusted_center.col_trusted_job_operation'),
        dataIndex: 'operation',
        name: 'operation',
        render: (_: any, record: any) => {
          return (
            <>
              <Button
                type="text"
                onClick={() => {
                  onLogClick(record);
                }}
              >
                {t('trusted_center.btn_inspect_logs')}
              </Button>
            </>
          );
        },
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [jobId],
  );

  return (
    <Drawer
      width={807}
      title={
        <span>{t('trusted_center.title_trusted_job_detail', { name: trustedJobInfo?.name })}</span>
      }
      visible={visible}
      onOk={() => {
        toggleVisible(false);
      }}
      onCancel={() => {
        toggleVisible(false);
      }}
    >
      {renderBasicInfo()}
      {renderInstanceInfo()}
    </Drawer>
  );

  function renderBasicInfo() {
    return (
      <>
        <h3>{t('trusted_center.title_base_info')}</h3>
        <PropertyList cols={6} colProportions={[1.5, 1, 1]} properties={displayedProps} />
      </>
    );
  }

  function renderInstanceInfo() {
    return (
      <>
        <h3>{t('trusted_center.title_instance_info')}</h3>
        <Table
          loading={trustedJobQuery.isFetching}
          size="small"
          rowKey="name"
          scroll={{ x: '100%' }}
          columns={columns}
          data={jobId ? jobList : []}
          pagination={{
            showTotal: true,
            pageSizeChangeResetCurrent: true,
            hideOnSinglePage: true,
          }}
        />
      </>
    );
  }

  function renderRuntime(trustedJobInfo: TrustedJob) {
    let isRunning = false;
    let isStopped = true;
    let runningTime = 0;

    const { status } = trustedJobInfo;
    const { PENDING, RUNNING, STOPPED, SUCCEEDED, FAILED } = TrustedJobStatus;
    isRunning = [RUNNING, PENDING].includes(status);
    isStopped = [STOPPED, SUCCEEDED, FAILED].includes(status);

    if (isRunning || isStopped) {
      const { finished_at, started_at } = trustedJobInfo;
      runningTime = isStopped ? finished_at! - started_at! : dayjs().unix() - started_at!;
    }
    return <CountTime time={runningTime} isStatic={!isRunning} />;
  }

  function onLogClick(pod: Pod) {
    const startTime = 0;
    window.open(`/v2/logs/pod/${jobId}/${pod.name}/${startTime}`, '_blank noopener');
  }

  function renderUnauthParticipantList(record: any) {
    return (
      <div>
        {Object.keys(record.participants_info.participants_map).map((key) => {
          return (
            <div>{`${key} ${
              AuthStatusMap[
                record.participants_info?.participants_map[key].auth_status as AuthStatus
              ]
            }`}</div>
          );
        })}
      </div>
    );
  }
};

export default ExportJobDetailDrawer;
