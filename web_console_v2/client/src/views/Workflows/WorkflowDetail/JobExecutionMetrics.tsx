import React, { FC, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import getMetricsSVG from 'assets/images/get-metrics.svg';
import emptySVG from 'assets/images/empty.svg';
import styled from './JobExecutionMetrics.module.less';
import { Button, Message, Spin } from '@arco-design/web-react';
import { useQuery } from 'react-query';
import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { fetchJobMpld3Metrics, fetchPeerJobMpld3Metrics } from 'services/workflow';
import queryClient from 'shared/queryClient';
import { Workflow } from 'typings/workflow';
import ErrorBoundary from 'components/ErrorBoundary';

type Props = {
  workflow?: Workflow;
  job: JobNodeRawData;
  isPeerSide: boolean;
  visible?: boolean;
  participantId?: ID;
};

const JobExecutionMetrics: FC<Props> = ({ job, workflow, visible, isPeerSide, participantId }) => {
  const { t } = useTranslation();

  const [chartsVisible, setChartsVisible] = useState(false);

  const metricsQ = useQuery(['fetchMetrics', job.id, chartsVisible, isPeerSide], fetcher, {
    refetchOnWindowFocus: false,
    cacheTime: 60 * 60 * 1000,
    retry: 2,
    enabled: chartsVisible && visible,
  });

  const chartMetrics = metricsQ.data;

  if (metricsQ.isError) {
    Message.error((metricsQ.error as any)?.message);
  }

  /**
   * When drawer's visibility or job id change
   * Check if metrics been fetched and cached recently,
   * if true, show result as before
   */
  useEffect(() => {
    const hasCache = !!queryClient.getQueryData(['fetchMetrics', job.id, true]);
    setChartsVisible(hasCache);
  }, [visible, job.id]);

  // Chart render effect
  useEffect(() => {
    import('mpld3/d3.v5.min.js')
      .then((d3) => {
        window.d3 = d3;
      })
      .then(() => import('mpld3'))
      .then((mpld3) => {
        if (chartMetrics?.data) {
          if (!mpld3) {
            Message.warning(t('workflow.msg_chart_deps_loading'));
            return;
          }
          chartMetrics.data.forEach((_, index) => {
            setTimeout(() => {
              mpld3.remove_figure(_targetChartId(index));
            }, 20);
          });
          try {
            chartMetrics.data.forEach((metric, index) => {
              const chartId = _targetChartId(index);
              setTimeout(() => {
                mpld3.draw_figure(chartId, metric);
              }, 20);
            });
          } catch (error) {
            Message.error(error.message);
          }
        }
      });

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartMetrics]);

  const isEmpty = chartMetrics?.data?.length === 0;
  const isPeerMetricsPublic = isPeerSide && workflow?.metric_is_public;
  const metricsVisible = isPeerMetricsPublic || !isPeerSide;

  return (
    <ErrorBoundary>
      <div data-display-chart={chartsVisible} className={styled.container}>
        <h3>{t('workflow.label_job_metrics')}</h3>

        {!metricsVisible && (
          <div className={styled.metric_not_public}>
            <p className={styled.explaination}>{t('workflow.placeholder_metric_not_public')}</p>
          </div>
        )}

        {!chartMetrics && metricsVisible && (
          <Spin loading={metricsQ.isFetching} style={{ width: '100%' }}>
            <div className={styled.placeholder}>
              <img src={getMetricsSVG} alt="fetch-metrics" />
              <p className={styled.explaination}>{t('workflow.placeholder_fetch_metrics')}</p>
              <Button
                className={styled.cta_button}
                type="primary"
                onClick={() => setChartsVisible(true)}
              >
                {t('workflow.btn_fetch_metrics')}
              </Button>
            </div>
          </Spin>
        )}

        {isEmpty && (
          <div className={styled.placeholder}>
            <img src={emptySVG} alt="fetch-metrics" />
            <p className={styled.explaination}> {t('workflow.placeholder_no_metrics')}</p>
            <Button
              className={styled.cta_button}
              loading={metricsQ.isFetching}
              type="primary"
              onClick={() => metricsQ.refetch()}
            >
              {t('workflow.btn_retry')}
            </Button>
          </div>
        )}

        {chartMetrics?.data?.map((_, index) => {
          return <div className={styled.chart_container} id={_targetChartId(index)} />;
        })}
      </div>
    </ErrorBoundary>
  );

  function fetcher() {
    if (isPeerSide) {
      if (workflow && workflow.uuid) {
        return fetchPeerJobMpld3Metrics(workflow.uuid, job.k8sName || job.name, participantId ?? 0);
      }

      throw new Error(t('workflow.msg_lack_workflow_infos'));
    }
    return fetchJobMpld3Metrics(job.id);
  }
};

function _targetChartId(index: number) {
  return `chart_${index}`;
}

export default JobExecutionMetrics;
