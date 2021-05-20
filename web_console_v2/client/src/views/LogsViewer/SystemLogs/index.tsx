import React, { FC, useEffect, useState } from 'react';
import PrintLogs from 'components/PrintLogs';
import { fetchPodNameList, fetchSystemLogs } from 'services/system';
import { Tabs } from 'antd';
import { useQuery } from 'react-query';

const { TabPane } = Tabs;

const SystemLogs: FC = () => {
  const podNameListQuery = useQuery(['fetchPodNameList'], () => fetchPodNameList());
  const [currentPodName, setCurrentPodName] = useState<string>('');
  const podNameList = podNameListQuery.data?.data;
  const isEmpty = podNameList?.length === 0 || podNameList === undefined;

  useEffect(() => {
    if (podNameList) {
      setCurrentPodName(podNameList[0]);
    }
  }, [podNameList]);
  return (
    <>
      <Tabs
        onChange={(activeKey: string) => {
          setCurrentPodName(activeKey);
        }}
      >
        {podNameList?.map((podName) => {
          return (
            <TabPane tab={podName} key={podName}>
              <PrintLogs
                logsFetcher={getLogs}
                refetchInterval={4000}
                queryKey={['getSystemLogs']}
              />
            </TabPane>
          );
        })}
      </Tabs>
      {isEmpty && <span>Pod name list is empty</span>}
    </>
  );

  async function getLogs() {
    if (!currentPodName) {
      return { data: ['Current pod name is undefined'] };
    }
    return fetchSystemLogs(500, currentPodName).catch((error) => {
      return { data: [error.message] };
    });
  }
};

export default SystemLogs;
