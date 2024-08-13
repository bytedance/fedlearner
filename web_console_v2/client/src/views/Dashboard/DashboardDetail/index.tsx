import React, { FC, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import SharedPageLayout from 'components/SharedPageLayout';
import styled from './index.module.less';
import { useQuery } from 'react-query';
import { fetchDashboardList } from 'services/operation';
import { Empty, Space, Spin, Tooltip } from '@arco-design/web-react';
import { IconSend } from '@arco-design/web-react/icon';
import CodeEditor from 'components/CodeEditor';

type Props = {};

const Dashboard: FC<Props> = () => {
  const { uuid } = useParams<{ uuid: string }>();
  const dashboardQuery = useQuery('fetchDashboardList', () => fetchDashboardList(), {});
  const dashboardURL = useMemo(() => {
    if (!dashboardQuery.data) {
      return '';
    }
    return (dashboardQuery.data?.data || []).find((item) => item.uuid === uuid)?.url;
  }, [dashboardQuery.data, uuid]);
  if (!uuid) {
    return (
      <SharedPageLayout title={'仪表盘'}>
        <div className={styled.container}>
          <Empty description={renderEmptyTips()} />
        </div>
      </SharedPageLayout>
    );
  }
  return (
    <SharedPageLayout
      title={'仪表盘'}
      rightTitle={
        <span>
          <button
            className="custom-text-button"
            onClick={() => {
              window.open(dashboardURL, '_blank');
            }}
          >
            <Tooltip position={'left'} trigger="hover" content="新页面打开">
              <IconSend />
            </Tooltip>
          </button>
        </span>
      }
    >
      <div className={styled.container}>
        {dashboardQuery.isFetching ? (
          <Spin style={{ display: 'block' }} />
        ) : (
          <iframe
            style={{
              width: '100%',
              height: '100%',
            }}
            title={'dashboard'}
            src={dashboardURL}
          />
        )}
      </div>
    </SharedPageLayout>
  );

  function renderEmptyTips() {
    return (
      <Space direction={'vertical'}>
        <h3>
          dashboard功能暂未开启，如需开启须确保此FLAG 「dashboard_enabled」 和环境变量
          「KIBANA_DASHBOARD_LIST」设置正确
        </h3>
        <div
          style={{
            height: '100px',
          }}
        >
          <CodeEditor
            language={'python'}
            isReadOnly={true}
            value={
              'FLAGS=\'{"dashboard_enabled": true}\'\n' +
              'KIBANA_DASHBOARD_LIST=\'[{"name": "overview", "uuid": "<uuid-of-kibana-dashboard>"}]\''
            }
          />
        </div>
      </Space>
    );
  }
};

export default Dashboard;
