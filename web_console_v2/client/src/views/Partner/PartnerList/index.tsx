import React, { FC, useState } from 'react';
import { useQuery } from 'react-query';

import { fetchSysInfo } from 'services/settings';
import { CONSTANTS } from 'shared/constants';

import { Tag, Tabs, Spin } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import SharedPageLayout, { RemovePadding } from 'components/SharedPageLayout';
import PartnerTable from './PartnerTable';

import styles from './index.module.less';

const PartnerList: FC = () => {
  const sysInfoQuery = useQuery(['fetchSysInfo'], () => fetchSysInfo(), {
    retry: 2,
    refetchOnWindowFocus: false,
  });

  const [activeKey] = useState<string>('partners');

  return (
    <SharedPageLayout title={'合作伙伴'}>
      <Spin loading={sysInfoQuery.isFetching}>
        <div className={styles.user_message}>
          <GridRow gap="12" style={{ maxWidth: '75%' }}>
            <div
              className={styles.avatar_container}
              data-name={sysInfoQuery.data?.data?.name?.slice(0, 1) ?? CONSTANTS.EMPTY_PLACEHOLDER}
            />
            <div>
              <h3>{sysInfoQuery.data?.data.name ?? CONSTANTS.EMPTY_PLACEHOLDER}</h3>
              <div>
                <Tag className={styles.tag_container}>
                  泛域名：{sysInfoQuery.data?.data?.domain_name ?? CONSTANTS.EMPTY_PLACEHOLDER}
                </Tag>
              </div>
            </div>
          </GridRow>
        </div>
      </Spin>
      <RemovePadding style={{ height: 48 }}>
        <Tabs defaultActiveTab={activeKey}>
          <Tabs.TabPane title="合作伙伴" key="partners" />
        </Tabs>
      </RemovePadding>
      <div>{activeKey === 'partners' && <PartnerTable />}</div>
    </SharedPageLayout>
  );
};

export default PartnerList;
