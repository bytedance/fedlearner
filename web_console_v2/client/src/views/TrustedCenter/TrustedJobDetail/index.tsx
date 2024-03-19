import React, { FC, useMemo, useState } from 'react';
import { Drawer, Table, Button, Tag, Tooltip } from '@arco-design/web-react';
import { useTranslation } from 'react-i18next';
import PropertyList from 'components/PropertyList';
import { TrustedJob, TrustedJobGroup, TrustedJobStatus } from 'typings/trustedCenter';
import { useQuery } from 'react-query';
import { fetchTrustedJob } from 'services/trustedCenter';
import { useGetCurrentProjectId } from 'hooks';
import { Pod, PodState } from 'typings/job';
import { fetchJobById } from 'services/workflow';
import { formatTimestamp } from 'shared/date';
import CONSTANTS from 'shared/constants';
import CountTime from 'components/CountTime';
import WhichAlgorithm from 'components/WhichAlgorithm';
import WhichDataset from 'components/WhichDataset';
import StateIndicator from 'components/StateIndicator';
import { getPodState } from 'views/Workflows/shared';
import dayjs from 'dayjs';
import './index.less';
import WhichParticipant from 'components/WhichParticipant';

export enum TResourceFieldType {
  MASTER = 'master',
  PS = 'ps',
  WORKER = 'worker',
}

export type TrustedJobProps = {
  visible: boolean;
  id?: ID;
  jobId?: ID;
  toggleVisible: (val: any) => void;
  group: TrustedJobGroup;
};

const TrustedJobDetail: FC<TrustedJobProps> = ({ visible, toggleVisible, id, jobId, group }) => {
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
        value: '可信计算',
        label: t('trusted_center.label_algorithm_type'),
      },
      {
        value: (
          <WhichAlgorithm
            id={trustedJobInfo?.algorithm_id || 0}
            uuid={trustedJobInfo?.algorithm_uuid}
            participantId={group?.algorithm_participant_id}
          />
        ),
        label: t('trusted_center.label_algorithm_select'),
      },
      {
        value: renderDatasetTooltip(group),
        label: t('trusted_center.col_trusted_job_dataset'),
      },
      {
        value: trustedJobInfo?.started_at
          ? formatTimestamp(trustedJobInfo?.started_at || 0)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: t('trusted_center.col_trusted_job_start_time'),
      },
      {
        value: trustedJobInfo?.finished_at
          ? formatTimestamp(trustedJobInfo?.finished_at || 0)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: t('trusted_center.col_trusted_job_end_time'),
      },
      {
        value: trustedJobInfo?.status ? renderRuntime(trustedJobInfo) : CONSTANTS.EMPTY_PLACEHOLDER,
        label: t('trusted_center.col_trusted_job_runtime'),
      },
      {
        value: (
          <div>
            {trustedJobInfo?.resource ? (
              <div>
                <Tag color="arcoblue">{TResourceFieldType.WORKER}</Tag>
                <span>{`${trustedJobInfo?.resource.cpu / 1000}CPU+${
                  trustedJobInfo?.resource.memory
                }GiB*${trustedJobInfo?.resource.replicas}个实例`}</span>
              </div>
            ) : (
              CONSTANTS.EMPTY_PLACEHOLDER
            )}
          </div>
        ),
        label: t('trusted_center.title_resource_config'),
      },
      {
        value:
          trustedJobInfo?.coordinator_id === 0 ? (
            t('trusted_center.label_coordinator_self')
          ) : (
            <WhichParticipant id={trustedJobInfo?.coordinator_id} />
          ),
        label: '发起方',
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

  function renderDatasetTooltip(record: TrustedJobGroup) {
    if (!record) {
      return CONSTANTS.EMPTY_PLACEHOLDER;
    }
    // without participant datasets
    if (record.participant_datasets.items?.length === 0) {
      return <WhichDataset.DatasetDetail id={record.dataset_id} />;
    }

    const hasMyDataset = record.dataset_id !== 0;
    let length = record.participant_datasets.items?.length || 0;
    if (hasMyDataset) {
      length += 1;
    }
    const datasets = record.participant_datasets.items!;
    const nameList = datasets.map((item) => {
      return item.name;
    });

    return (
      <div className="display-dataset__tooltip">
        {hasMyDataset ? (
          <WhichDataset.DatasetDetail id={record.dataset_id} />
        ) : (
          <div style={{ marginTop: '3px' }}>{nameList[0]}</div>
        )}
        {length > 1 ? (
          <Tooltip
            position="top"
            trigger="hover"
            color="#FFFFFF"
            content={nameList.map((item, index) => {
              if (!hasMyDataset && index === 0) return <></>;
              return (
                <>
                  <Tag style={{ marginTop: '5px' }} key={index}>
                    {item}
                  </Tag>
                  <br />
                </>
              );
            })}
          >
            <Tag>{`+${length - 1}`}</Tag>
          </Tooltip>
        ) : (
          <></>
        )}
      </div>
    );
  }
};

export default TrustedJobDetail;
