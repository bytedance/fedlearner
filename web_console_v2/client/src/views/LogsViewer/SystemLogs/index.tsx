import React, { FC, useEffect, useState } from 'react';
import PrintLogs from 'components/PrintLogs';
import { fetchPodNameList, fetchSystemLogs } from 'services/system';
import { Tabs } from '@arco-design/web-react';
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
            <TabPane title={podName} key={podName}>
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

  async function getLogs(tailLines = 500) {
    if (!currentPodName) {
      return { data: ['Current pod name is undefined'] };
    }
    return fetchSystemLogs(tailLines, currentPodName).catch((error) => {
      return { data: [error.message] };
    });
  }
};

export default SystemLogs;
