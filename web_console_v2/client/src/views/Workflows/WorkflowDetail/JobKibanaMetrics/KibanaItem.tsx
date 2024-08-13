import React, { FC, memo, useContext, useEffect, useState } from 'react';
import styled from './KibanaItem.module.less';
import KibanaParamsForm from './KibanaParamsForm';
import KibanaEmbeddedChart from './KibanaChart/EmbeddedChart';
import { Grid, Message, Spin } from '@arco-design/web-react';
import { JobType } from 'typings/job';
import { fetchJobEmbedKibanaSrc, fetchPeerKibanaMetrics } from 'services/workflow';
import { JobExecutionDetailsContext } from '../JobExecutionDetailsDrawer';
import { to } from 'shared/helpers';
import { KiabanaMetrics, KibanaChartType, KibanaQueryParams } from 'typings/kibana';
import { useToggle } from 'react-use';
import { useTranslation } from 'react-i18next';
import KibanaLineChart from './KibanaChart/LineChart';

const Row = Grid.Row;
const Col = Grid.Col;

const { Rate, Ratio, Numeric, Time, Timer } = KibanaChartType;

const typesForPeerSideJob = [Ratio, Numeric];
const typesForDataJoinJob = [Rate, Ratio, Numeric, Time, Timer];
const typesForNonDataJoinJob = [Ratio, Numeric, Time, Timer];

const KibanaItem: FC = memo(() => {
  /** Need a empty string as placeholder on left side */
  const { t } = useTranslation();
  const [embedSrcs, setEmbedSrcs] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<KiabanaMetrics>([]);
  const [configuring, toggleConfiguring] = useToggle(true);
  const [fetching, toggleFetching] = useToggle(false);

  const { isPeerSide, job, workflow, participantId } = useContext(JobExecutionDetailsContext);

  useEffect(() => {
    setEmbedSrcs([]);
    setMetrics([]);
    toggleConfiguring(true);
  }, [job?.id, toggleConfiguring]);

  const isEmpty = isPeerSide ? metrics.length === 0 : embedSrcs.length === 0;

  return (
    <div className={styled.container}>
      <Row gutter={20}>
        <Col span={configuring ? 12 : 24}>
          <Spin loading={fetching} style={{ width: '100%' }}>
            <div className={styled.chart_container} data-is-fill={!configuring}>
              {isEmpty ? (
                <div className={styled.not_loaded_placeholder}>
                  {t('workflow.placeholder_fill_kibana_form')}
                </div>
              ) : isPeerSide ? (
                <KibanaLineChart
                  isFill={!configuring}
                  label=""
                  metrics={metrics}
                  onEditParams={onEditParamsClick}
                />
              ) : (
                <>
                  {embedSrcs.map((src) => (
                    <KibanaEmbeddedChart
                      src={`${src}`}
                      isFill={!configuring}
                      onEditParams={onEditParamsClick}
                      onOpenNewWindow={onNewWindowClick}
                    />
                  ))}
                </>
              )}
            </div>
          </Spin>
        </Col>

        {configuring && (
          <Col span={12}>
            <KibanaParamsForm
              types={
                isPeerSide
                  ? typesForPeerSideJob
                  : _isDataJoinJob(job?.job_type)
                  ? typesForDataJoinJob
                  : typesForNonDataJoinJob
              }
              onConfirm={onConfirm}
              onPreview={onPreview}
              onNewWindowPreview={onNewWindowPreview}
            />
          </Col>
        )}
      </Row>
    </div>
  );

  async function fetchEmbedSrcList(values: KibanaQueryParams): Promise<string[]> {
    toggleFetching(true);
    const [res, err] = await to(fetchJobEmbedKibanaSrc(job.id, values));
    toggleFetching(false);
    if (err) {
      Message.error(err.message);
      return [];
    }

    if (Array.isArray(res.data) && res.data.length) {
      return res.data;
    }

    Message.warning(t('workflow.msg_no_available_kibana'));

    return [];
  }

  /** For peer side, we need to render chart by ourself due to kibana is unaccessiable */
  async function fetchMetrics(values: KibanaQueryParams) {
    toggleFetching(true);
    const [res, err] = await to(
      fetchPeerKibanaMetrics(workflow?.uuid!, job.k8sName || job.name, participantId ?? 0, values),
    );
    toggleFetching(false);
    if (err) {
      Message.error(err.message);
      return;
    }

    setMetrics(res.data);
  }

  async function onConfirm(values: KibanaQueryParams) {
    if (isPeerSide) {
      fetchMetrics(values);
      toggleConfiguring(false);
      return;
    }

    const srcs = await fetchEmbedSrcList(values);
    setEmbedSrcs(srcs);

    toggleConfiguring(false);
  }
  async function onPreview(values: KibanaQueryParams) {
    if (isPeerSide) {
      fetchMetrics(values);
      return;
    }
    const srcs = await fetchEmbedSrcList(values);
    setEmbedSrcs(srcs);
  }

  async function onNewWindowPreview(values: KibanaQueryParams) {
    // Peer side shouldn't have this action
    if (isPeerSide) return;

    const srcs = await fetchEmbedSrcList(values);

    srcs.forEach(async (src) => {
      window.open(src, '_blank noopener');
    });
  }

  function onEditParamsClick() {
    toggleConfiguring(true);
  }
  function onNewWindowClick(src: string) {
    if (src) {
      window.open(src, '_blank noopener');
    }
  }
});

function _isDataJoinJob(type: JobType) {
  return [JobType.DATA_JOIN, JobType.PSI_DATA_JOIN].includes(type);
}

export default KibanaItem;
