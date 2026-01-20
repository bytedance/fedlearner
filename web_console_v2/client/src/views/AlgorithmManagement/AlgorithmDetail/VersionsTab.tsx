import React, { FC, useMemo, useState } from 'react';
import { Table, Button, Link, Drawer, Empty } from '@arco-design/web-react';
import AlgorithmInfo from 'components/AlgorithmDrawer/AlgorithmInfo';
import {
  AlgorithmProject,
  Algorithm,
  EnumAlgorithmProjectSource,
  AlgorithmVersionStatus,
} from 'typings/algorithm';
import { formatTimestamp } from 'shared/date';
import MoreActions from 'components/MoreActions';
import { CONSTANTS } from 'shared/constants';
import StateIndicator, { StateTypes } from 'components/StateIndicator';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantId } from 'hooks';
import { useQuery } from 'react-query';
import { fetchAlgorithmList, fetchPeerAlgorithmList } from 'services/algorithm';
import styled from './index.module.less';

type TTableParams = {
  onPreviewClick: (algorithm: Algorithm) => void;
  onPublishClick: (algorithm: Algorithm) => void;
  onUnpublishClick: (algorithm: Algorithm) => void;
  onDeleteClick: (algorithm: Algorithm) => void;
  onDownloadClick: (algorithm: Algorithm) => void;
  algorithmProjectDetail: AlgorithmProject;
  isParticipant?: boolean;
};

const calcStateIndicatorProps = (
  state: AlgorithmVersionStatus,
): { type: StateTypes; text: string; tip?: string } => {
  const tip = '';
  const stateMap = new Map();
  stateMap.set(AlgorithmVersionStatus.UNPUBLISHED, {
    text: '未发布',
    type: 'gold',
  });
  stateMap.set(AlgorithmVersionStatus.PUBLISHED, {
    text: '已发布',
    type: 'success',
  });
  stateMap.set(AlgorithmVersionStatus.PENDING, {
    text: '待审批',
    type: 'goprocessingld',
  });
  stateMap.set(AlgorithmVersionStatus.APPROVED, {
    text: '已通过',
    type: 'processing',
  });
  stateMap.set(AlgorithmVersionStatus.DECLINED, {
    text: '已拒绝',
    type: 'error',
  });
  return {
    ...stateMap.get(state),
    tip,
  };
};

const getTableProps = ({
  onPreviewClick,
  onPublishClick,
  onUnpublishClick,
  onDeleteClick,
  onDownloadClick,
  algorithmProjectDetail,
  isParticipant,
}: TTableParams) => {
  const cols = [
    {
      dataIndex: 'version',
      title: '版本号',
      render(version: number) {
        return `V${version}`;
      },
    },
    {
      dataIndex: 'id',
      title: '版本配置',
      render(id: string, record: Algorithm) {
        return <Link onClick={() => onPreviewClick(record)}>点击查看</Link>;
      },
    },
    !isParticipant &&
      ({
        title: '状态',
        dataIndex: 'status',
        name: 'status',
        width: 150,
        render: (state: AlgorithmVersionStatus, record: any) => {
          return <StateIndicator {...calcStateIndicatorProps(state)} />;
        },
      } as any),
    !isParticipant &&
      ({
        dataIndex: 'username',
        title: '创建者',
      } as any),
    {
      dataIndex: 'comment',
      title: '描述',
      render(val: string) {
        return val || CONSTANTS.EMPTY_PLACEHOLDER;
      },
    },
    {
      dataIndex: 'created_at',
      title: '发版时间',
      render(val: number) {
        return formatTimestamp(val);
      },
    },
    !isParticipant && {
      dataIndex: 'operation',
      title: '操作',
      render(_: any, record: Algorithm) {
        return (
          <>
            {(record.status === AlgorithmVersionStatus.PUBLISHED ||
              record.status === AlgorithmVersionStatus.APPROVED) && (
              <Button
                className={styled.version_list_button}
                type="text"
                size="small"
                onClick={() => {
                  onUnpublishClick(record);
                }}
                disabled={algorithmProjectDetail.source !== EnumAlgorithmProjectSource.USER}
              >
                {'撤销发布'}
              </Button>
            )}
            {(record.status === AlgorithmVersionStatus.UNPUBLISHED ||
              record.status === AlgorithmVersionStatus.DECLINED) && (
              <Button
                className={styled.version_list_button}
                type="text"
                size="small"
                onClick={() => {
                  onPublishClick(record);
                }}
                disabled={algorithmProjectDetail.source !== EnumAlgorithmProjectSource.USER}
              >
                {'发布'}
              </Button>
            )}
            <MoreActions
              actionList={[
                {
                  label: '下载',
                  onClick: () => {
                    onDownloadClick(record);
                  },
                },
                {
                  label: '删除',
                  onClick: () => {
                    onDeleteClick(record);
                  },
                  danger: true,
                  disabled:
                    algorithmProjectDetail.source !== EnumAlgorithmProjectSource.USER ||
                    record.status === AlgorithmVersionStatus.PENDING,
                },
              ]}
            />
          </>
        );
      },
    },
  ].filter(Boolean);

  return cols;
};

type Props = {
  id?: ID;
  detail?: AlgorithmProject;
  isParticipant?: boolean;
  isBuiltIn?: boolean;
  onPublishClick: (algorithm: Algorithm) => void;
  onUnpublishClick: (algorithm: Algorithm) => void;
  onReleaseClick: () => void;
  onDeleteClick: (algorithm: Algorithm) => void;
  onDownloadClick: (algorithm: Algorithm) => void;
};

const VersionsTab: FC<Props> = ({
  id,
  detail,
  isParticipant,
  isBuiltIn,
  onPublishClick,
  onUnpublishClick,
  onReleaseClick,
  onDeleteClick,
  onDownloadClick,
}) => {
  const projectId = useGetCurrentProjectId();
  const participantId = useGetCurrentProjectParticipantId();
  const listQuery = useQuery(
    ['fetchAlgorithmList', projectId, participantId, id],
    () => {
      if (isParticipant) {
        return fetchPeerAlgorithmList(projectId, participantId, { algorithm_project_uuid: id! });
      }
      return fetchAlgorithmList(isBuiltIn ? 0 : projectId, { algo_project_id: id! });
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );
  const [previewAlgorithm, setPreviewAlgorithm] = useState<Algorithm>();

  const formattedAlgorithms = useMemo(() => {
    if (!listQuery.data?.data) {
      return [];
    }
    return listQuery.data?.data;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listQuery.data?.data]);

  if (!detail) {
    return null;
  }
  return (
    <>
      <Table
        className="custom-table custom-table-left-side-filter"
        hover={false}
        data={formattedAlgorithms}
        noDataElement={
          <Empty
            description={
              <>
                暂无已发版的算法版本.
                {!isBuiltIn && (
                  <Button
                    className={styled.version_list_button}
                    size="small"
                    type="text"
                    style={{ marginLeft: '0.2em' }}
                    onClick={() => {
                      onReleaseClick();
                    }}
                  >
                    去发版
                  </Button>
                )}
              </>
            }
          />
        }
        columns={getTableProps({
          onPreviewClick,
          onPublishClick,
          onUnpublishClick,
          onDeleteClick,
          onDownloadClick,
          algorithmProjectDetail: detail,
          isParticipant: isParticipant,
        })}
        rowKey="uuid"
      />
      <Drawer
        closable
        onCancel={() => setPreviewAlgorithm(undefined)}
        width={1200}
        visible={Boolean(previewAlgorithm)}
        title={`算法版本 V${previewAlgorithm?.version}`}
      >
        <AlgorithmInfo isParticipant={isParticipant} type="algorithm" detail={previewAlgorithm} />
      </Drawer>
    </>
  );

  function onPreviewClick(algorithm: Algorithm) {
    setPreviewAlgorithm(algorithm);
  }
};

export default VersionsTab;
