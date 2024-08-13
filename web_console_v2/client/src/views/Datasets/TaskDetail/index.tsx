import React, { FC, useCallback, useMemo, useRef, useState } from 'react';
import { useHistory } from 'react-router';
import { Alert, Message, Spin, Statistic, Tag, Progress } from '@arco-design/web-react';
import ReactFlow, {
  Controls,
  Edge,
  FlowElement,
  isNode,
  Node,
  OnLoadParams,
  Position,
} from 'react-flow-renderer';
import { LabelStrong } from 'styles/elements';
import DatasetNode from './DatasetNode';
import TagNode from './TagNode';

import { fetchDatasetJobDetail } from 'services/dataset';

import { useQuery } from 'react-query';
import {
  useGetCurrentDomainName,
  useGetCurrentProjectId,
  useGetCurrentProjectParticipantList,
} from 'hooks';
import { DataJobBackEndTypeToLabelMap, isDataImport, isDataJoin, isDataAnalyzer } from '../shared';
import {
  DataJobBackEndType,
  Dataset,
  DatasetKindBackEndType,
  DatasetKindLabel,
  ParticipantDataset,
} from 'typings/dataset';

import { DatasetDetailSubTabs } from '../DatasetDetail';
import { ParticipantType } from 'typings/participant';
import { ImportNode } from './ImportNode';
import { JobDetailSubTabs } from 'views/Datasets/NewDatasetJobDetail';
import './index.less';

export enum NodeType {
  DATASET_MY = 'dataset_my',
  DATASET_PARTICIPANT = 'dataset_participant',
  DATASET_PROCESSED = 'dataset_processed',
  Tag = 'tag',
  UPLOAD = 'upload',
  DOWNLOAD = 'download',
  LIGHT_CLIENT = 'light_client',
}

export type DatasetNodeData = {
  title: string;
  dataset_name: string;
  dataset_uuid: string;
  dataset_job_uuid?: string;
  workflow_uuid?: string;
  isActive?: boolean;
  job_id?: ID;
};

type Props = {
  datasetId?: ID;
  datasetJobId?: ID;
  onNodeClick?: (
    element: FlowElement<DatasetNodeData>,
    datasetMapper?: { [key: string]: Dataset },
  ) => void;
  errorMessage?: string;
  isProcessedDataset?: boolean;
  middleJump: Boolean;
  className?: string;
  isOldData?: boolean; // 是否是老数据
  isShowTitle?: boolean;
  isShowRatio?: boolean; // 是否展示求交率等信息
};

const nodeTypes = {
  [NodeType.DATASET_MY]: DatasetNode,
  [NodeType.DATASET_PARTICIPANT]: DatasetNode,
  [NodeType.DATASET_PROCESSED]: DatasetNode,
  [NodeType.Tag]: TagNode,
  [NodeType.UPLOAD]: ImportNode,
  [NodeType.DOWNLOAD]: DatasetNode,
  [NodeType.LIGHT_CLIENT]: DatasetNode,
};

export const BASE_X = 0;
export const BASE_Y = 100;
export const WIDTH_DATASET_NODE = 260;
export const WIDTH_TAG_NODE = 120;
export const WIDTH_GAP = 120;
export const HEIGHT_DATASET_NODE = 56;
export const HEIGHT_TAG_NODE = 24;

const TaskDetail: FC<Props> = ({
  datasetId,
  datasetJobId,
  onNodeClick,
  errorMessage,
  isProcessedDataset = false,
  middleJump,
  className,
  isOldData = false,
  isShowTitle = true,
  isShowRatio = true,
}) => {
  const history = useHistory();
  const projectId = useGetCurrentProjectId();
  const currentDomainName = useGetCurrentDomainName();
  const participantList = useGetCurrentProjectParticipantList();

  const [intersectionRate, setIntersectionRate] = useState(0);
  const [intersectionNumber, setIntersectionNumber] = useState(0);
  const [myAmountOfData, setMyAmountOfData] = useState(0);
  const myDatasetUuidToInfoMap = useRef<{
    [uuid: string]: Dataset;
  }>({});
  const myParticipantDatasetUuidToDatasetInfoMap = useRef<{
    [uuid: string]: ParticipantDataset;
  }>({});
  const myResultDatasetUuidToInfoMap = useRef<{
    [uuid: string]: Dataset;
  }>({});

  const getLeftNodeName = (jobKind: DataJobBackEndType) => {
    switch (jobKind) {
      case DataJobBackEndType.EXPORT:
        return '结果数据集';
      case DataJobBackEndType.IMPORT_SOURCE:
        return '本地上传';
      default:
        return '我方数据集';
    }
  };

  const getRightNodeName = (jobKind: DataJobBackEndType) => {
    switch (jobKind) {
      case DataJobBackEndType.EXPORT:
        return '导出地址';
      case DataJobBackEndType.IMPORT_SOURCE:
        return '原始数据集';
      default:
        return '结果数据集';
    }
  };

  const datasetJobDetailQuery = useQuery(
    ['fetchDatasetJobDetail', projectId, datasetJobId],
    () => fetchDatasetJobDetail(projectId!, datasetJobId!),
    {
      refetchOnWindowFocus: false,
      retry: 2,
      enabled: Boolean(projectId && datasetJobId),
      onSuccess(res) {
        const { input_data_batch_num_example, output_data_batch_num_example, kind } = res.data;
        setIntersectionRate((prev) => {
          if (input_data_batch_num_example === 0) {
            return 0;
          }
          return parseFloat(
            ((output_data_batch_num_example / input_data_batch_num_example) * 100).toFixed(2),
          );
        });

        setIntersectionNumber((prev) => {
          return output_data_batch_num_example;
        });

        setMyAmountOfData((prev) => {
          const myAmountOfData = isDataImport(kind)
            ? output_data_batch_num_example
            : input_data_batch_num_example;
          return myAmountOfData || 0;
        });
      },
    },
  );

  const leftNodeType = useMemo(() => {
    const getLeftNodeType = (jobKind: DataJobBackEndType) => {
      switch (jobKind) {
        case DataJobBackEndType.EXPORT:
          return NodeType.DATASET_PROCESSED;
        case DataJobBackEndType.IMPORT_SOURCE:
          return NodeType.UPLOAD;
        default:
          return NodeType.DATASET_MY;
      }
    };
    // set empty and default value to <import>
    if (!datasetJobDetailQuery?.data?.data) {
      return NodeType.UPLOAD;
    }
    return getLeftNodeType(datasetJobDetailQuery.data.data?.kind);
  }, [datasetJobDetailQuery.data]);

  const rightNodeType = useMemo(() => {
    const getRightNodeType = (jobKind: DataJobBackEndType) => {
      switch (jobKind) {
        case DataJobBackEndType.EXPORT:
          return NodeType.DOWNLOAD;
        case DataJobBackEndType.IMPORT_SOURCE:
          return NodeType.DATASET_MY;
        default:
          return NodeType.DATASET_PROCESSED;
      }
    };
    // set empty and default value to <export>
    if (!datasetJobDetailQuery?.data?.data) {
      return NodeType.DOWNLOAD;
    }
    return getRightNodeType(datasetJobDetailQuery.data.data?.kind);
  }, [datasetJobDetailQuery.data]);

  const onMyDatasetAPISuccess = useCallback((uuid: ID, dataset: Dataset) => {
    myDatasetUuidToInfoMap.current[uuid] = dataset;
  }, []);
  const onParticipantAPISuccess = useCallback(
    (uuid: ID, participantDataset: ParticipantDataset) => {
      myParticipantDatasetUuidToDatasetInfoMap.current[uuid] = participantDataset;
    },
    [],
  );
  const onResultDatasetAPISuccess = useCallback((uuid: ID, dataset: Dataset) => {
    myResultDatasetUuidToInfoMap.current[uuid] = dataset;
  }, []);

  const elementList = useMemo(() => {
    const isLightClient = (curParticipant: string) => {
      if (Array.isArray(participantList)) {
        const filterParticipant = participantList.filter((item) =>
          item?.domain_name?.includes(curParticipant),
        );
        if (filterParticipant.length) {
          return filterParticipant[0].type === ParticipantType.LIGHT_CLIENT;
        }
      }
      return false;
    };

    if (!datasetJobDetailQuery.data || !currentDomainName) {
      return [];
    }

    const datasetJobDetail = datasetJobDetailQuery.data.data;
    const rawDatasetObject = datasetJobDetail?.global_configs?.global_configs ?? {};

    let myDatasetElementList: Node[] = [];
    let participantDatasetElementList: Node[] = [];
    const kindElementList: Node[] = [];
    const processedDatasetElementList: Node[] = [];
    const edgeElementList: Edge[] = [];

    // col 1: raw dataset
    Object.keys(rawDatasetObject).forEach((key, index) => {
      const rawDatasetInfo = rawDatasetObject[key];

      if (currentDomainName.indexOf(key) > -1) {
        myDatasetElementList.push({
          id: `c1-${rawDatasetInfo.dataset_uuid}`,
          sourcePosition: Position.Right,
          type: leftNodeType,
          data: {
            title: getLeftNodeName(datasetJobDetail.kind),
            dataset_uuid: rawDatasetInfo.dataset_uuid,
            onAPISuccess: onMyDatasetAPISuccess,
            isActive: !isProcessedDataset,
          },
          position: { x: BASE_X, y: BASE_Y },
        });
      } else {
        // check whether the participant is light client
        const isCurLightClient = isLightClient(key);
        participantDatasetElementList.push({
          id: `c1-${isCurLightClient ? key : rawDatasetInfo.dataset_uuid}`,
          sourcePosition: Position.Right,
          type: isCurLightClient ? NodeType.LIGHT_CLIENT : NodeType.DATASET_PARTICIPANT,
          data: {
            title: isCurLightClient ? (
              <>
                合作伙伴数据集{' '}
                <Tag className="task-detail-tag" color="arcoblue">
                  轻量
                </Tag>
              </>
            ) : (
              `合作伙伴数据集 - ${key}`
            ),
            dataset_uuid: isCurLightClient ? key : rawDatasetInfo.dataset_uuid,
            onAPISuccess: isCurLightClient ? null : onParticipantAPISuccess,
          },
          position: { x: BASE_X, y: BASE_Y + HEIGHT_DATASET_NODE * 2 },
        });
      }
    });

    myDatasetElementList = myDatasetElementList.map((item, index) => ({
      ...item,
      position: { x: BASE_X, y: BASE_Y + HEIGHT_DATASET_NODE * 2 * index },
    }));

    const PARTICIPANT_BASE_Y =
      myDatasetElementList.length > 0
        ? myDatasetElementList[myDatasetElementList.length - 1].position.y + 2 * HEIGHT_DATASET_NODE
        : BASE_Y;

    participantDatasetElementList = participantDatasetElementList.map((item, index) => ({
      ...item,
      position: {
        x: BASE_X,
        y: PARTICIPANT_BASE_Y + HEIGHT_DATASET_NODE * 2 * index,
      },
    }));

    const rawDatasetList = [...myDatasetElementList, ...participantDatasetElementList].map(
      (item, index) => ({
        ...item,
        id: `c1-${index}`,
      }),
    );

    // col 2: kind
    kindElementList.push({
      id: 'c2-1',
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
      type: NodeType.Tag,
      data: {
        title: DataJobBackEndTypeToLabelMap[datasetJobDetail.kind] || 'Unknown',
        kind: datasetJobDetail.kind,
        dataset_job_uuid: datasetJobDetail.uuid,
        workflow_uuid: datasetJobDetail.workflow_id,
        job_id: middleJump ? datasetJobId : null, // 中间不可跳转的话，数据不传job_id， 兼容置灰
      },
      position: {
        x: WIDTH_DATASET_NODE + WIDTH_GAP,
        y:
          BASE_Y +
          Math.floor((2 * rawDatasetList.length - 1) / 2) * HEIGHT_DATASET_NODE +
          (HEIGHT_DATASET_NODE - HEIGHT_TAG_NODE) / 2,
      },
    });

    // col 3: processed dataset
    processedDatasetElementList.push({
      id: 'c3-1',
      targetPosition: Position.Left,
      type: rightNodeType,
      data: {
        title: getRightNodeName(datasetJobDetail.kind),
        dataset_name: datasetJobDetail.result_dataset_name,
        dataset_uuid: datasetJobDetail.result_dataset_uuid,
        isActive: isProcessedDataset,
        onAPISuccess: onResultDatasetAPISuccess,
      },
      position: {
        x: WIDTH_DATASET_NODE + WIDTH_GAP * 2 + WIDTH_TAG_NODE,
        y: BASE_Y + Math.floor((2 * rawDatasetList.length - 1) / 2) * HEIGHT_DATASET_NODE - 1.5,
      },
    });

    // edge
    if (kindElementList.length > 0) {
      rawDatasetList.forEach((item) => {
        edgeElementList.push({
          id: `e|${item.id}_c2-1`,
          source: `${item.id}`,
          target: 'c2-1',
          type: 'smoothstep',
          animated: true,
        });
      });
    }

    if (kindElementList.length > 0 && processedDatasetElementList.length > 0) {
      edgeElementList.push({
        id: `e|c2-1_c3-1`,
        source: 'c2-1',
        target: 'c3-1',
        type: 'smoothstep',
        animated: true,
      });
    }

    return [
      ...rawDatasetList,
      ...kindElementList,
      ...processedDatasetElementList,
      ...edgeElementList,
    ];
  }, [
    participantList,
    datasetJobId,
    onResultDatasetAPISuccess,
    datasetJobDetailQuery.data,
    currentDomainName,
    isProcessedDataset,
    onMyDatasetAPISuccess,
    onParticipantAPISuccess,
    leftNodeType,
    rightNodeType,
    middleJump,
  ]);

  const isShowErrorMessage = errorMessage;

  return (
    <Spin loading={datasetJobDetailQuery.isFetching} className={className}>
      <div>
        {isShowTitle && (
          <LabelStrong fontSize={14} isBlock={true}>
            任务流程
          </LabelStrong>
        )}

        <div className="react-flow-container">
          {isShowRatio && (
            <div className="statistic-group-container">
              {isDataJoin(datasetJobDetailQuery.data?.data?.kind) && (
                <>
                  <Progress
                    className="statistic-progress"
                    percent={intersectionRate ? intersectionRate : 0}
                    size="large"
                    type="circle"
                    status="normal"
                    trailColor="var(--color-primary-light-1)"
                    formatText={(percent: number) => {
                      return (
                        <Statistic
                          className="statistic-rate-item"
                          extra="求交率"
                          value={intersectionRate}
                          suffix="%"
                          groupSeparator
                        />
                      );
                    }}
                  />

                  <Statistic
                    className="statistic-item"
                    title="交集数"
                    value={intersectionNumber || 0}
                    groupSeparator
                  />
                </>
              )}

              {!isDataAnalyzer(datasetJobDetailQuery.data?.data?.kind) && (
                <Statistic
                  className="statistic-item"
                  title="我方数据量"
                  value={myAmountOfData || 0}
                  groupSeparator
                />
              )}
            </div>
          )}

          {elementList.length > 0 && (
            <ReactFlow
              elements={elementList}
              onLoad={onReactFlowLoad}
              onElementClick={(_, element: FlowElement) => onElementsClick(element)}
              nodesDraggable={false}
              nodesConnectable={false}
              zoomOnScroll={false}
              zoomOnPinch={false}
              zoomOnDoubleClick={false}
              minZoom={1}
              maxZoom={1}
              defaultZoom={1}
              nodeTypes={nodeTypes}
            >
              <Controls showZoom={false} showInteractive={false} />
            </ReactFlow>
          )}
        </div>
        {isShowErrorMessage && (
          <>
            <LabelStrong fontSize={14} isBlock={true} style={{ marginBottom: 12 }}>
              错误信息
            </LabelStrong>
            <Alert type="error" showIcon={false} content={errorMessage} />
          </>
        )}
      </div>
    </Spin>
  );

  function onReactFlowLoad(reactFlowInstance: OnLoadParams) {
    // Fits the view port so that all nodes are visible
    reactFlowInstance!.fitView();
  }
  async function onElementsClick(element: FlowElement<DatasetNodeData>) {
    const allNodeMapper = {
      ...myDatasetUuidToInfoMap.current,
      ...myResultDatasetUuidToInfoMap.current,
    };
    if (element && isNode(element)) {
      onNodeClick?.(element, allNodeMapper);
      switch (element?.type) {
        case NodeType.DATASET_MY:
          const datasetInfo = allNodeMapper[element?.data?.dataset_uuid ?? ''];
          if (datasetInfo?.id) {
            history.push(
              `/datasets/${
                datasetInfo?.dataset_kind === DatasetKindBackEndType.PROCESSED
                  ? DatasetKindLabel.PROCESSED
                  : DatasetKindLabel.RAW
              }/detail/${datasetInfo.id}/${DatasetDetailSubTabs.DatasetJobDetail}`,
            );
          }
          break;
        case NodeType.Tag:
          if (middleJump && element?.data?.job_id) {
            try {
              if (isOldData) {
                history.push(`/datasets/job_detail/${element?.data?.job_id}`);
              } else {
                history.push(
                  `/datasets/${datasetId}/new/job_detail/${element?.data?.job_id}/${JobDetailSubTabs.TaskProcess}`,
                );
              }
            } catch (error) {
              Message.error(error.message);
            }
          }
          break;
        default:
          break;
      }
    }
  }
};

export default TaskDetail;
