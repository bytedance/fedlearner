import React, { FC, useMemo } from 'react';
import FeatureInfoDrawer, {
  formatChartData,
  METRIC_KEY_TRANSLATE_MAP,
} from 'components/DataPreview/StructDataTable/FeatureInfoDrawer';
import { useQuery } from 'react-query';
import { fetchFeatureInfo } from 'services/dataset';
import { floor } from 'lodash-es';

type Props = {
  id: ID;
  batchId: ID;
  activeKey?: string;
  visible: boolean;
  onClose: () => void;
  toggleDrawerVisible: (val: boolean) => void;
};

const StructDataPreview: FC<Props> = ({
  id,
  batchId,
  activeKey,
  visible,
  onClose,
  toggleDrawerVisible,
}) => {
  const featInfoQuery = useQuery(
    ['fetchFeatureInfo', activeKey, id, batchId],
    () => fetchFeatureInfo(id, batchId, activeKey!),
    {
      enabled: Boolean(activeKey) && visible,
      refetchOnWindowFocus: false,
    },
  );
  const featData = useMemo(() => {
    if (!activeKey || !featInfoQuery.data) return undefined;

    const data = featInfoQuery.data?.data;

    // Add custom filed missing_rate
    const metrics = data?.metrics ?? {};
    if (
      Object.prototype.hasOwnProperty.call(metrics, 'count') &&
      Object.prototype.hasOwnProperty.call(metrics, 'missing_count') &&
      !Object.prototype.hasOwnProperty.call(metrics, 'missing_rate')
    ) {
      const missingCount = Number(metrics.missing_count) || 0;
      const allCount = missingCount + (Number(metrics.count) || 0);
      // Calc missing_rate
      metrics['missing_rate'] = String(floor((missingCount / allCount) * 100, 2));
    }

    const table = Object.entries(metrics).map(([key, value]) => {
      return {
        key: METRIC_KEY_TRANSLATE_MAP[key],
        value: key === 'missing_rate' ? value + '%' : floor(Number(value), 3),
      };
    });

    const hist = formatChartData(data.hist.x ?? [], [{ data: data.hist.y ?? [], label: '数据集' }]);

    return { table, hist };
  }, [featInfoQuery.data, activeKey]);
  return (
    <FeatureInfoDrawer
      data={featData?.table}
      histData={featData?.hist}
      featureKey={activeKey}
      loading={featInfoQuery.isFetching}
      visible={visible}
      toggleVisible={toggleDrawerVisible}
      onClose={onClose}
    />
  );
};

export default StructDataPreview;
