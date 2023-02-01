import React, { FC, useState, useMemo, useEffect } from 'react';
import { Grid, Button, Space, Tabs, Tag, Message } from '@arco-design/web-react';
import { useHistory, useParams, Redirect } from 'react-router-dom';
import { forceToRefreshQuery } from 'shared/queryClient';
import { useMutation, useQuery } from 'react-query';

import VersionsTab from './VersionsTab';
import AlgorithmInfo from 'components/AlgorithmDrawer/AlgorithmInfo';

import BackButton from 'components/BackButton';
import MoreActions from 'components/MoreActions';
import PropertyList from 'components/PropertyList';
import SharedPageLayout from 'components/SharedPageLayout';
import {
  fetchAlgorithmList,
  fetchPeerAlgorithmList,
  fetchPeerAlgorithmProjectById,
  fetchProjectDetail,
  getFullAlgorithmDownloadHref,
  postPublishAlgorithm,
  publishAlgorithm,
} from 'services/algorithm';
import { formatTimestamp } from 'shared/date';
import {
  Algorithm,
  EnumAlgorithmProjectSource,
  AlgorithmReleaseStatus,
  AlgorithmVersionStatus,
} from 'typings/algorithm';
import showAlgorithmSendingModal from '../AlgorithmSendModal';
import AlgorithmType from 'components/AlgorithmType';

import styled from './index.module.less';
import { AlgorithmManagementTabType } from 'typings/modelCenter';
import { Avatar, deleteConfirm, unpublishConfirm } from '../shared';
import { CONSTANTS } from 'shared/constants';
import request from 'libs/request';
import { useGetCurrentProjectId, useGetCurrentProjectParticipantId } from 'hooks';

const { Row, Col } = Grid;

enum AlgorithmDetailTabType {
  FILES = 'files',
  VERSIONS = 'versions',
}

enum algorithmDetailType {
  MY = 'my',
  BUILT_IN = 'built-in',
  PARTICIPANT = 'participant',
}

type TRouteParams = {
  id: string;
  tabType: AlgorithmDetailTabType;
  algorithmDetailType: algorithmDetailType;
};

const AlgorithmDetail: FC = () => {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();
  const participantId = useGetCurrentProjectParticipantId();
  const params = useParams<TRouteParams>();
  const [activeKey, setActiveKey] = useState<AlgorithmDetailTabType>();
  const [algoNumber, setAlgoNumber] = useState<number>(0);
  const isParticipant = params.algorithmDetailType === algorithmDetailType.PARTICIPANT;
  const isBuiltIn = params.algorithmDetailType === algorithmDetailType.BUILT_IN;
  const queryKeys = ['algorithmDetail', params.id];

  const detailQuery = useQuery(
    queryKeys,
    () => {
      if (isParticipant) {
        return fetchPeerAlgorithmProjectById(projectId, participantId, params.id).then(
          (res) => res.data,
        );
      }
      return fetchProjectDetail(params.id).then((res) => res.data);
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const listQuery = useQuery(
    ['fetchAlgorithmList', projectId, participantId, params.id],
    () => {
      if (isParticipant) {
        return fetchPeerAlgorithmList(projectId, participantId, {
          algorithm_project_uuid: params.id,
        });
      }
      return fetchAlgorithmList(isBuiltIn ? 0 : projectId, { algo_project_id: params.id });
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
      onSuccess(res) {
        if (res.data) {
          setAlgoNumber(res.data.length);
        }
      },
    },
  );

  const detail = detailQuery.data;

  const publishMutation = useMutation(
    (comment: string) => {
      return postPublishAlgorithm(params.id, comment);
    },
    {
      onSuccess() {
        if (activeKey === AlgorithmDetailTabType.FILES) {
          onTabChange(AlgorithmDetailTabType.VERSIONS);
        } else {
          forceToRefreshQuery([...queryKeys] as string[]);
        }
      },
    },
  );

  const displayedProps = useMemo(
    () => [
      {
        value: detail?.type ? (
          <div style={{ marginTop: '-4px' }}>
            <AlgorithmType type={detail.type} />
          </div>
        ) : (
          CONSTANTS.EMPTY_PLACEHOLDER
        ),
        label: '类型',
      },
      {
        value: detail?.username || CONSTANTS.EMPTY_PLACEHOLDER,
        label: '创建者',
        hidden: isParticipant,
      },
      {
        value: detail?.updated_at
          ? formatTimestamp(detail.updated_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '更新时间',
      },
      {
        value: detail?.created_at
          ? formatTimestamp(detail.created_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '创建时间',
      },
    ],
    [detail, isParticipant],
  );

  const algorithms = useMemo(() => {
    if (!listQuery.data) {
      return [];
    }
    return listQuery.data.data || [];
  }, [listQuery.data]);

  useEffect(() => {
    setActiveKey(params.tabType);
  }, [params.tabType]);

  let tabContent: React.ReactNode;

  switch (params.tabType) {
    case AlgorithmDetailTabType.FILES:
      tabContent = <AlgorithmInfo type="algorithm_project" detail={detail} />;
      break;
    case AlgorithmDetailTabType.VERSIONS:
      tabContent = detail ? (
        <VersionsTab
          onPublishClick={handleAlgorithmPublish}
          onUnpublishClick={handleAlgorithmVersionUnpublish}
          onReleaseClick={onRelease}
          onDeleteClick={handleAlgorithmVersionDelete}
          onDownloadClick={handleAlgorithmVersionDownload}
          detail={detail}
          id={params.id}
          isParticipant={isParticipant}
          isBuiltIn={isBuiltIn}
        />
      ) : null;
      break;
    default:
      tabContent = null;
      break;
  }

  return (
    <SharedPageLayout
      title={
        <BackButton
          onClick={() => history.push(`/algorithm-management/${AlgorithmManagementTabType.MY}`)}
        >
          {'算法仓库'}
        </BackButton>
      }
      cardPadding={0}
    >
      <div className={styled.padding_container}>
        <Row>
          <Col span={12}>
            <Space size="medium">
              <Avatar
                data-name={detail?.name ? detail.name.slice(0, 1) : CONSTANTS.EMPTY_PLACEHOLDER}
              />
              <div>
                <h3 className={styled.styled_name}>{detail?.name ?? '....'}</h3>
                <Space className={styled.comment}>
                  {renderAlgorithmStatus(detail)}
                  {detail?.comment ?? CONSTANTS.EMPTY_PLACEHOLDER}
                </Space>
              </div>
            </Space>
          </Col>
          <Col className={styled.header_col} span={12}>
            {isParticipant ? (
              <></>
            ) : (
              <Space>
                <Button
                  type="primary"
                  disabled={detail?.source !== EnumAlgorithmProjectSource.USER}
                  onClick={() => {
                    history.push(`/algorithm-management/edit?id=${detail?.id}`);
                  }}
                >
                  {'编辑'}
                </Button>
                {detail?.release_status === AlgorithmReleaseStatus.UNRELEASED && (
                  <Button
                    loading={publishMutation.isLoading}
                    onClick={onRelease}
                    disabled={detail?.source !== EnumAlgorithmProjectSource.USER}
                  >
                    {'发版'}
                  </Button>
                )}
                <MoreActions
                  actionList={[
                    {
                      label: '发布最新版本',
                      onClick: () => {
                        if (algorithms.length > 0) {
                          onPublishAlgorithm(algorithms[0]);
                        }
                      },
                      disabled:
                        detail?.latest_version === 0 ||
                        detail?.source !== EnumAlgorithmProjectSource.USER ||
                        algorithms.length === 0 ||
                        algorithms[0]?.status === AlgorithmVersionStatus.PUBLISHED,
                    },
                  ]}
                />
              </Space>
            )}
          </Col>
        </Row>
        <PropertyList cols={6} colProportions={[1, 1, 1, 1]} properties={displayedProps} />
      </div>
      <Tabs activeTab={activeKey} onChange={onTabChange}>
        {isParticipant ? (
          <></>
        ) : (
          <Tabs.TabPane title={'算法文件'} key={AlgorithmDetailTabType.FILES} />
        )}
        <Tabs.TabPane
          title={
            <>
              {'版本列表'}{' '}
              <Tag
                color={activeKey === AlgorithmDetailTabType.VERSIONS ? 'arcoblue' : ''}
                className={styled.styled_version_amount_tag}
              >
                {algoNumber}
              </Tag>
            </>
          }
          key={AlgorithmDetailTabType.VERSIONS}
        />
      </Tabs>
      <div className={styled.content}>{tabContent}</div>
      {!params.tabType ? (
        <Redirect
          to={`/algorithm-management/detail/${params.id}/${AlgorithmDetailTabType.FILES}`}
        />
      ) : null}
    </SharedPageLayout>
  );

  function renderAlgorithmStatus(detail: any) {
    if (isParticipant || isBuiltIn) {
      return <></>;
    }

    if (detail?.release_status === AlgorithmReleaseStatus.RELEASED) {
      return (
        <Tag size="small" color="green">
          已发版
        </Tag>
      );
    }

    return (
      <Tag size="small" color="orange">
        未发版
      </Tag>
    );
  }

  function onTabChange(val: string) {
    setActiveKey(val as AlgorithmDetailTabType);
    detailQuery.refetch();
    history.replace(
      `/algorithm-management/detail/${params.id}/${val}/${params.algorithmDetailType}`,
    );
  }

  function onRelease() {
    showAlgorithmSendingModal(
      detail!,
      async (comment: string) => {
        return publishMutation.mutate(comment);
      },
      () => {},
      true,
    );
  }

  function refetchProjectDetail() {
    listQuery.refetch();
    detailQuery.refetch();
  }

  function onPublishAlgorithm(algorithm: Algorithm) {
    handleAlgorithmPublish(algorithm);
  }

  function handleAlgorithmPublish(algorithm: Algorithm) {
    showAlgorithmSendingModal(
      algorithm,
      (comment: string) => {
        return publishAlgorithm(projectId, algorithm.id, { comment }).then((resp) => {
          refetchProjectDetail();
        });
      },
      () => {},
    );
  }

  async function handleAlgorithmVersionUnpublish(algorithm: Algorithm) {
    try {
      await unpublishConfirm(projectId!, algorithm);
      forceToRefreshQuery([...queryKeys] as string[]);
      refetchProjectDetail();
    } catch (e) {
      Message.error(e.message);
    }
  }

  async function handleAlgorithmVersionDelete(algorithm: Algorithm) {
    try {
      await deleteConfirm(algorithm, false);
      forceToRefreshQuery([...queryKeys] as string[]);
      refetchProjectDetail();
    } catch (e) {
      Message.error(e.message);
    }
  }

  async function handleAlgorithmVersionDownload(algorithm: Algorithm) {
    try {
      const tip = await request.download(getFullAlgorithmDownloadHref(algorithm.id));
      tip && Message.info(tip);
    } catch (error) {
      Message.error(error.message);
    }
  }
};

export default AlgorithmDetail;
