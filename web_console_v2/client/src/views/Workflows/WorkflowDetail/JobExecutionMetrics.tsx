import { loadScript } from 'shared/helpers';
import React, { FC, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import getMetricsSVG from 'assets/images/get-metrics.svg';
import emptySVG from 'assets/images/empty.svg';
import styled from 'styled-components';
import { Button, message, Spin } from 'antd';
import { useQuery } from 'react-query';
import { JobNodeRawData } from 'components/WorkflowJobsCanvas/types';
import { fetchJobMpld3Metrics, fetchPeerJobMpld3Metrics } from 'services/workflow';
import queryClient from 'shared/queryClient';
import { Workflow } from 'typings/workflow';
import { MixinFlexAlignCenter } from 'styles/mixins';
import ErrorBoundary from 'antd/lib/alert/ErrorBoundary';

const Container = styled.div`
  margin-top: 30px;
  margin-bottom: 20px;
`;
const Header = styled.h3``;
const ChartContainer = styled.div`
  height: 480px;
  overflow: hidden;
  text-align: center;
  line-height: 200px;
`;
const Placeholder = styled.div`
  display: flex;
  flex-direction: column;
  width: 280px;
  height: 400px;
  margin: auto;

  > img {
    width: 230px;
    margin-top: auto;
  }
`;
const MetricsNotPublic = styled.div`
  ${MixinFlexAlignCenter()}
  display: flex;
  height: 160px;
`;
const Explaination = styled.p`
  margin-top: 10px;
  font-size: 12px;
  text-align: center;
  color: var(--textColorSecondary);
`;
const CTAButton = styled(Button)`
  display: block;
  margin: 0 auto auto;
`;

declare global {
  interface Window {
    mpld3: {
      draw_figure: (containerId: string, data: any) => void;
      remove_figure: (containerId: string) => void;
    };
  }
}
type Props = {
  workflow?: Workflow;
  job: JobNodeRawData;
  isPeerSide: boolean;
  visible?: boolean;
};

const JobExecutionMetrics: FC<Props> = ({ job, workflow, visible, isPeerSide }) => {
  const { t } = useTranslation();

  const [mpld3, setMpld3Intance] = useState((null as any) as Window['mpld3']);
  const [chartsVisible, setChartsVisible] = useState(false);

  // Load deps only one time
  useEffect(() => {
    _loadDependencies().then(() => {
      setMpld3Intance(window.mpld3);
    });
  }, []);

  const metricsQ = useQuery(['fetchMetrics', job.id, chartsVisible, isPeerSide], fetcher, {
    refetchOnWindowFocus: false,
    staleTime: 60 * 60 * 1000, // 1 hours cache
    cacheTime: 60 * 60 * 1000,
    retry: 2,
    enabled: chartsVisible && visible && Boolean(mpld3),
  });

  const chartMetrics = metricsQ.data;

  if (metricsQ.isError) {
    message.error((metricsQ.error as any)?.message);
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
    if (chartMetrics?.data) {
      if (!mpld3) {
        message.warn(t('workflow.msg_chart_deps_loading'));
        return;
      }
      clearChart();
      try {
        chartMetrics.data.forEach((metric, index) => {
          const chartId = _targetChartId(index);
          setTimeout(() => {
            mpld3.draw_figure(chartId, metric);
          }, 20);
        });
      } catch (error) {
        message.error(error.message);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartMetrics, mpld3]);

  const isEmpty = !chartMetrics?.data || chartMetrics?.data.length === 0;
  const isPeerMetricsPublic = isPeerSide && workflow?.metric_is_public;
  const metricsVisible = isPeerMetricsPublic || !isPeerSide;

  return (
    <ErrorBoundary>
      <Container data-display-chart={chartsVisible}>
        <Header>{t('workflow.label_job_metrics')}</Header>

        {!metricsVisible && (
          <MetricsNotPublic>
            <Explaination>{t('workflow.placeholder_metric_not_public')}</Explaination>
          </MetricsNotPublic>
        )}

        {!chartMetrics && metricsVisible && (
          <Spin spinning={metricsQ.isFetching}>
            <Placeholder>
              <img src={getMetricsSVG} alt="fetch-metrics" />
              <Explaination>{t('workflow.placeholder_fetch_metrics')}</Explaination>
              <CTAButton type="primary" onClick={() => setChartsVisible(true)}>
                {t('workflow.btn_fetch_metrics')}
              </CTAButton>
            </Placeholder>
          </Spin>
        )}

        {isEmpty && (
          <Placeholder>
            <img src={emptySVG} alt="fetch-metrics" />
            <Explaination> {t('workflow.placeholder_no_metrics')}</Explaination>
            <CTAButton
              loading={metricsQ.isFetching}
              type="primary"
              onClick={() => metricsQ.refetch()}
            >
              {t('workflow.btn_retry')}
            </CTAButton>
          </Placeholder>
        )}

        {chartMetrics?.data.map((_, index) => {
          return <ChartContainer id={_targetChartId(index)} />;
        })}
      </Container>
    </ErrorBoundary>
  );

  function clearChart() {
    if (!chartMetrics || !mpld3) return;

    chartMetrics.data.forEach((_, index) => {
      setTimeout(() => {
        mpld3.remove_figure(_targetChartId(index));
      }, 20);
    });
  }

  function fetcher() {
    if (isPeerSide) {
      if (workflow && workflow.uuid) {
        return fetchPeerJobMpld3Metrics(workflow.uuid, job.k8sName || job.name);
      }

      throw new Error(t('workflow.msg_lack_workflow_infos'));
    }
    return fetchJobMpld3Metrics(job.id);
  }
};

function _loadDependencies() {
  return loadScript('https://d3js.org/d3.v5.min.js').then(() => {
    return loadScript('https://mpld3.github.io/js/mpld3.v0.5.2.js');
  });
}

function _targetChartId(index: number) {
  return `chart_${index}`;
}

export default JobExecutionMetrics;
