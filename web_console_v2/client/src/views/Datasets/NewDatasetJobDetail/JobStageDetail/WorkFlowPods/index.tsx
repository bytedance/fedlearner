import React, { useMemo, useState } from 'react';
import { LabelStrong } from 'styles/elements';
import { Button, Message, Popover, Radio, Tooltip } from '@arco-design/web-react';
import { useQuery } from 'react-query';
import { useGetCurrentProjectId, useTablePaginationWithUrlState } from 'hooks';
import { fetchJobById, getWorkflowDetailById } from 'services/workflow';
import { TIME_INTERVAL } from 'shared/constants';
import { get } from 'lodash-es';
import { Pod, PodState } from 'typings/job';
import { Table } from '@arco-design/web-react';
import ClickToCopy from 'components/ClickToCopy';
import StateIndicator from 'components/StateIndicator';
import { getPodState, podStateFilters } from 'views/Workflows/shared';
import { formatTimestamp } from 'shared/date';
import { Link } from 'react-router-dom';
import styled from './index.module.less';
type TWorkFlowPods = {
  workFlowId?: ID;
};

export default function WorkFlowPods(prop: TWorkFlowPods) {
  const { workFlowId } = prop;
  const { paginationProps, reset } = useTablePaginationWithUrlState({
    urlStateOption: { navigateMode: 'replace' },
  });
  const projectId = useGetCurrentProjectId();
  const [selectJobId, setSelectJobId] = useState<ID>();
  const workFlowDetail = useQuery(
    ['fetch_workflow_detail', projectId, workFlowId],
    () => {
      if (!workFlowId) {
        return Promise.resolve({ data: {} });
      }
      if (!projectId) {
        Message.info('请选择工作区');
        return Promise.resolve({ data: {} });
      }
      return getWorkflowDetailById(workFlowId!, projectId);
    },
    {
      cacheTime: 1,
      refetchInterval: TIME_INTERVAL.CONNECTION_CHECK,
      onSuccess: (data) => {
        const jobIds = get(data, 'data.job_ids') || [];
        if (jobIds.length) {
          setSelectJobId((pre) => {
            return jobIds.indexOf(selectJobId) > -1 ? pre : jobIds[0];
          });
        }
      },
    },
  );

  const jobDetail = useQuery(
    ['fetchJobById', selectJobId],
    () => fetchJobById(Number(selectJobId)),
    {
      enabled: Boolean(selectJobId),
    },
  );

  const jobList = useMemo(() => {
    if (!workFlowDetail.data) {
      return [];
    }
    const jobIds = get(workFlowDetail.data, 'data.job_ids') || [];
    const jobNames = get(workFlowDetail.data, 'data.config.job_definitions') || [];
    const jobs = get(workFlowDetail.data, 'data.jobs') || [];
    return jobIds.map((item: ID, index: number) => {
      const { error_message, state } = jobs[index];
      return {
        label: jobNames[index].name,
        value: item,
        hasError:
          error_message &&
          (error_message.app || JSON.stringify(error_message.pods) !== '{}') &&
          state !== 'COMPLETED',
        errorMessage: error_message,
      };
    });
  }, [workFlowDetail.data]);

  const jobData = useMemo(() => {
    return get(jobDetail, 'data.data.pods') || ([] as Pod[]);
  }, [jobDetail]);

  const handleOnChangeJob = (val: ID) => {
    setSelectJobId(() => val);
    reset();
  };

  const columns = [
    {
      title: 'Pod',
      dataIndex: 'name',
      key: 'name',
      width: 400,
      render: (val: string) => {
        return <ClickToCopy text={val}>{val}</ClickToCopy>;
      },
    },
    {
      title: '运行状态',
      dataIndex: 'state',
      key: 'state',
      ...podStateFilters,
      width: 200,
      render: (_: PodState, record: Pod) => {
        return <StateIndicator {...getPodState(record)} />;
      },
    },
    {
      title: '创建时间',
      dataIndex: 'creation_timestamp',
      key: 'creation_timestamp',
      width: 150,
      sorter(a: Pod, b: Pod) {
        return a.creation_timestamp - b.creation_timestamp;
      },
      render: (val: number) => {
        return formatTimestamp(val);
      },
    },
    {
      title: '操作',
      dataIndex: 'actions',
      key: 'actions',
      width: 150,
      render: (_: any, record: Pod) => {
        return (
          <Link target={'_blank'} to={`/logs/pod/${selectJobId}/${record.name}`}>
            日志
          </Link>
        );
      },
    },
  ];

  return (
    <>
      <div className={styled.workflow_pods_header}>
        <LabelStrong fontSize={14} isBlock={true}>
          实例信息
        </LabelStrong>
        <Radio.Group onChange={handleOnChangeJob} size="small" type="button" value={selectJobId}>
          {jobList.map((item: any) => {
            return (
              <Radio key={item.value} value={item.value}>
                {item.hasError ? (
                  <Tooltip content={renderErrorMessage(item.errorMessage)}>
                    <span className={styled.job_detail_state_indicator}>
                      <span className={styled.dot} />
                      {item.label}
                    </span>
                  </Tooltip>
                ) : (
                  item.label
                )}
              </Radio>
            );
          })}
        </Radio.Group>
        <Popover
          trigger="hover"
          position="br"
          content={
            <span>
              <div className={styled.job_detail_more_title}>工作流</div>
              <Link
                className={styled.job_detail_more_link}
                to={`/workflow-center/workflows/${workFlowId}`}
              >
                点击查看工作流
              </Link>
              <div className={styled.job_detail_more_title}>工作流 ID</div>
              <div className={styled.job_detail_more_content}>{workFlowId}</div>
            </span>
          }
        >
          <Button className={styled.job_detail_more_button} type="text">
            更多信息
          </Button>
        </Popover>
      </div>
      {jobList.length > 0 ? (
        <Table
          rowKey={'name'}
          className={'custom-table custom-table-left-side-filter'}
          loading={jobDetail.isFetching}
          data={jobData}
          columns={columns}
          pagination={{
            ...paginationProps,
          }}
          onChange={(pagination, sorter, filters, extra) => {
            if (extra.action === 'filter') {
              reset();
            }
          }}
        />
      ) : null}
    </>
  );
  function renderErrorMessage(errorMessage: any) {
    const { app, pods } = errorMessage;
    return (
      <div className={styled.job_detail_error_wrapper}>
        <h3 className={styled.job_detail_error_title}>Main Error: {app}</h3>
        {Object.entries(pods).map(([pod, error], index) => (
          <div className={styled.job_detail_error_item} key={index}>
            <div>Pod: {pod}</div>
            <div>Error: {error}</div>
          </div>
        ))}
      </div>
    );
  }
}
