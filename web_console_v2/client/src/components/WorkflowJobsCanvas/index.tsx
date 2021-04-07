import React, {
  useEffect,
  useState,
  forwardRef,
  useImperativeHandle,
  ForwardRefRenderFunction,
  useCallback,
} from 'react';
import * as WorkflowJobNodes from './JobNodes';
import { ChartNodeType, JobNode, ChartNodeStatus, ChartNodes, ChartElements } from './types';
import { convertToChartElements } from './helpers';
import ReactFlow, {
  Background,
  BackgroundVariant,
  isNode,
  OnLoadParams,
  FlowElement,
  useStoreActions,
  useStoreState,
  Controls,
  ReactFlowState,
} from 'react-flow-renderer';
import { Container } from './elements';
import { ChartWorkflowConfig } from 'typings/workflow';
import { cloneDeep } from 'lodash';
import { message } from 'antd';
import i18n from 'i18n';
import { useResizeObserver } from 'hooks';
import { Side } from 'typings/app';

type Props = {
  workflowConfig: ChartWorkflowConfig;
  nodeType: ChartNodeType;
  side?: Side; // NOTE: When the nodeType is 'fork', side is required
  selectable?: boolean;
  onJobClick?: (node: JobNode) => void;
  onCanvasClick?: () => void;
};
type UpdateInheritanceParams = {
  id: string;
  whetherInherit: boolean;
};
type UpdateStatusParams = {
  id: string;
  status: ChartNodeStatus;
};
type UpdateDisabledParams = {
  id: string;
  disabled: boolean;
};

export type ChartExposedRef = {
  nodes: ChartNodes;
  updateNodeStatusById: (params: UpdateStatusParams) => void;
  updateNodeDisabledById: (params: UpdateDisabledParams) => void;
  updateNodeInheritanceById: (params: UpdateInheritanceParams) => void;
  setSelectedNodes: (nodes: ChartNodes) => void;
};

const WorkflowJobsCanvas: ForwardRefRenderFunction<ChartExposedRef | undefined, Props> = (
  { workflowConfig, nodeType, side, selectable = true, onJobClick, onCanvasClick },
  parentRef,
) => {
  const isForkMode = nodeType === 'fork';
  if (isForkMode && !side) {
    console.error(
      "[WorkflowJobsCanvas]: Detect that current type is FORK but the `side` prop has't been assigned",
    );
  }
  const [chartInstance, setChartInstance] = useState<OnLoadParams>();
  const [elements, setElements] = useState<ChartElements>([]);
  // ☢️ WARNING: since we using react-flow hooks here,
  // an ReactFlowProvider is REQUIRED to wrap this component inside
  const jobNodes = (useStoreState((store: ReactFlowState) => store.nodes) as unknown) as ChartNodes;
  const setSelectedElements = useStoreActions((actions) => actions.setSelectedElements);

  // To decide if need to re-generate jobElements, look out that re-gen elements
  // will lead all nodes loose it's status!!💣
  //
  // Q: why not put workflowConfig directly as the dependent?
  // A: At workflowConfig's inner may contains variables' value
  // and will change during user configuring, but we do not want that lead
  // re-generate chart elements
  const workflowIdentifyString = workflowConfig.job_definitions
    .map((item) => item.name + item.mark || '')
    .concat(workflowConfig.variables?.map((item) => item.name) || [])
    .join('|');

  useEffect(() => {
    const jobElements = convertToChartElements(
      {
        /**
         * In workflow detail page workflowConfig.job_definitions are not only job_definitions
         * they will contain execution details as well
         */
        jobs: workflowConfig.job_definitions,
        variables: workflowConfig.variables || [],
        data: {
          side,
          // When fork type, inherit initially set to true, status to Success
          status: isForkMode ? ChartNodeStatus.Success : ChartNodeStatus.Pending,
        },
      },
      { type: nodeType, selectable },
    );
    setElements(jobElements);
    // eslint-disable-next-line
  }, [nodeType, selectable, workflowIdentifyString]);

  const resizeHandler = useCallback(() => {
    chartInstance?.fitView();
  }, [chartInstance]);

  const resizeTargetRef = useResizeObserver(resizeHandler);

  useImperativeHandle(parentRef, () => {
    return {
      nodes: jobNodes,
      updateNodeStatusById: updateNodeStatus,
      updateNodeDisabledById: updateNodeDisabled,
      updateNodeInheritanceById: updateNodeInheritance,
      setSelectedNodes: setSelectedElements,
    };
  });

  return (
    <Container ref={resizeTargetRef as any}>
      <ReactFlow
        elements={elements}
        onLoad={onLoad}
        onElementClick={(_, element: FlowElement) => onElementsClick(element)}
        onPaneClick={onCanvasClick}
        nodesDraggable={false}
        zoomOnScroll={false}
        zoomOnDoubleClick={false}
        minZoom={1}
        maxZoom={1}
        nodeTypes={WorkflowJobNodes}
      >
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} color="#E1E6ED" />
        <Controls showZoom={false} showInteractive={false} />
      </ReactFlow>
    </Container>
  );

  function onElementsClick(element: FlowElement) {
    if (isNode(element)) {
      onJobClick && onJobClick(element as JobNode);
    }
  }
  function onLoad(_reactFlowInstance: OnLoadParams) {
    setChartInstance(_reactFlowInstance!);
    // Fit view at next tick
    // TODO: implement nextTick
    setImmediate(() => {
      _reactFlowInstance!.fitView();
    });
  }
  function areTheySomeUninheritable(nodeIds: string[]) {
    return nodeIds.some((id) => elements.find((item) => item.id === id)?.data?.inherited === false);
  }
  function updateNodeStatus(params: UpdateStatusParams) {
    if (!params.id) return;

    setElements((els) => {
      return (els as ChartElements).map((el) => {
        if (el.id === params.id) {
          el.data = {
            ...el.data,
            status: params.status,
          };
        }
        return el;
      });
    });
  }
  function updateNodeDisabled(params: UpdateDisabledParams) {
    if (!params.id) return;

    setElements((els) => {
      return (els as ChartElements).map((el) => {
        if (el.id === params.id) {
          el.data = {
            ...el.data,
            disabled: params.disabled,
          };
        }
        return el;
      });
    });
  }
  function updateNodeInheritance({ id, whetherInherit }: UpdateInheritanceParams) {
    if (nodeType !== 'fork' || !id) {
      return;
    }
    const nextElements = cloneDeep(elements as JobNode[]);
    const target = nextElements.find((item) => item.id === id);

    if (!target) return;

    const itDependsOn = target?.data.raw.dependencies.map((item) => item.source);

    if (itDependsOn.length && areTheySomeUninheritable(itDependsOn)) {
      message.warning({
        // the key is used for making sure only one toast is allowed to show on the screen
        key: 'NOP_due_to_upstreaming_uninheritable',
        content: i18n.t('workflow.msg_upstreaming_nonreusable'),
        duration: 2000,
      });
      return;
    }

    target.data.inherited = whetherInherit;

    // Collect dependent chain
    const depsChainCollected: string[] = [];

    depsChainCollected.push(target?.id!);

    nextElements.forEach((item) => {
      if (!isNode(item) || item.data.isGlobal) return;

      const hasAnyDependentOnPrevs = item.data.raw.dependencies.find((dep) => {
        return depsChainCollected.includes(dep.source);
      });

      if (hasAnyDependentOnPrevs) {
        item.data.inherited = whetherInherit;

        depsChainCollected.push(item.id);
      }
    });

    setElements(nextElements);
  }
};

export default forwardRef(WorkflowJobsCanvas);
