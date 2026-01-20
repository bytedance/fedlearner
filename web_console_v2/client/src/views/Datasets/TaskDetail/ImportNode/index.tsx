import React, { FC, useMemo } from 'react';
import { Handle, Position, NodeComponentProps } from 'react-flow-renderer';
import { useQuery } from 'react-query';
import { fetchDatasetList, fetchDataSourceDetail } from 'services/dataset';
import { Label, LabelStrong } from 'styles/elements';
import { Spin } from '@arco-design/web-react';
import { FILTER_OPERATOR_MAPPER, filterExpressionGenerator } from '../../shared';
import ClickToCopy from 'components/ClickToCopy';
import styled from './index.module.less';

export type Props = NodeComponentProps<{
  title: string;
  dataset_name: string;
  dataset_uuid?: string;
  onAPISuccess?: (uuid: string, data?: any) => void;
  isActive?: boolean;
}>;

export const ImportNode: FC<Props> = ({ data, targetPosition, sourcePosition, type }) => {
  const datasetListQuery = useQuery(
    ['fetchDatasetList', data.dataset_uuid],
    () =>
      fetchDatasetList({
        filter: filterExpressionGenerator(
          {
            uuid: data.dataset_uuid,
          },
          FILTER_OPERATOR_MAPPER,
        ),
      }),
    {
      enabled: Boolean(data.dataset_uuid),
      refetchOnWindowFocus: false,
      retry: 2,
      onSuccess(res) {
        data.dataset_uuid && data?.onAPISuccess?.(data.dataset_uuid, res.data?.[0] ?? undefined);
      },
    },
  );

  const dataSourceDetailQuery = useQuery(
    ['data_source_detail_query', datasetListQuery],
    () =>
      fetchDataSourceDetail({
        id: datasetListQuery.data?.data?.[0].id!,
      }),
    {
      enabled: Boolean(
        datasetListQuery.data?.data?.[0]?.id || datasetListQuery.data?.data?.[0]?.id === 0,
      ),
      refetchOnWindowFocus: false,
      retry: 2,
    },
  );

  const [title, content] = useMemo(() => {
    const localTitle = '本地上传';
    const dataSourceTitle = '数据源上传';
    const noTitle = '导入任务';
    const noContent = '数据集信息未找到';
    if (!dataSourceDetailQuery?.data?.data) {
      return [noTitle, noContent];
    }
    const { name, url, is_user_upload } = dataSourceDetailQuery.data.data;
    const title = is_user_upload ? localTitle : `${dataSourceTitle}-${name}`;
    const content = is_user_upload ? <ClickToCopy text={url}>{url}</ClickToCopy> : url;
    return [title, content];
  }, [dataSourceDetailQuery]);

  return (
    <div className={`${styled.container} ${data?.isActive && styled.active}`}>
      <Label
        style={{
          wordBreak: 'break-all',
        }}
        isBlock
      >
        {dataSourceDetailQuery.isFetching ? <Spin /> : title}
      </Label>
      <LabelStrong
        isBlock
        fontSize={14}
        style={{
          wordBreak: 'break-all',
        }}
      >
        {dataSourceDetailQuery.isFetching ? <Spin /> : content}
      </LabelStrong>
      {targetPosition && (
        <Handle type="target" className={styled.handle_dot} position={Position.Left} />
      )}
      {sourcePosition && (
        <Handle type="source" className={styled.handle_dot} position={Position.Right} />
      )}
    </div>
  );
};
