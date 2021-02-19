import React, {
  useEffect,
  useState,
  forwardRef,
  useImperativeHandle,
  ForwardRefRenderFunction,
  useCallback,
} from 'react';
import WorkflowJobNode from './WorkflowJobNode';
import {
  ChartNodeType,
  NodeDataRaw,
  JobNode,
  JobNodeStatus,
  ChartNodes,
  ChartElements,
} from './types';
import { convertToChartElements } from './helpers';
import styled from 'styled-components';
import ReactFlow, {
  Background,
  BackgroundVariant,
  isNode,
  OnLoadParams,
  FlowElement,
  useStoreActions,
  useStoreState,
  Controls,
} from 'react-flow-renderer';

import { WorkflowConfig } from 'typings/workflow';
import { cloneDeep } from 'lodash';
import { message } from 'antd';
import i18n from 'i18n';
import { MixinSquare } from 'styles/mixins';
import { useResizeObserver } from 'hooks';

const Container = styled.div`
  position: relative;
  /* TODO: remove the hard-coded 48px of chart header */
  height: ${(props: any) => `calc(100% - ${props.top || '0px'} - 48px)`};
  background-color: var(--gray1);

  /* react flow styles override */
  .react-flow__node {
    border-radius: 4px;
    font-size: 1em;
    text-align: initial;
    background-color: transparent;
    cursor: initial;

    &-global,
    &-execution,
    &-fork,
    &-config {
      &.selected {
        --selected-background: #f2f6ff;
        --selected-border-color: var(--primaryColor);
      }
    }

    &.selectable {
      cursor: pointer;

      &:hover {
        filter: drop-shadow(0px 4px 10px #e0e0e0);
      }
    }
  }
  .react-flow__handle {
    width: 6px;
    height: 6px;
    opacity: 0;
  }
  .react-flow__edge {
    &-path {
      stroke: var(--gray4);
    }
  }
  .react-flow__controls {
    top: 20px;
    right: 20px;
    left: auto;
    bottom: auto;
    box-shadow: none;

    &-button {
      ${MixinSquare(27)}
      border-radius: 4px;
      border-bottom: none;
      box-shadow: 0 2px 10px -2px rgba(0, 0, 0, 0.2);
    }
  }
`;

type Props = {
  workflowConfig: WorkflowConfig<NodeDataRaw>;
  nodeType: ChartNodeType;
  side?: string; // NOTE: When the nodeType is 'fork', side is required
  selectable?: boolean;
  onJobClick?: (node: JobNode) => void;
  onCanvasClick?: () => void;
};
type updateInheritanceParams = {
  id: string;
  whetherInherit: boolean;
};
type updateStatusParams = {
  id: string;
  status: JobNodeStatus;
};

export type ChartExposedRef = {
  nodes: ChartNodes;
  updateNodeStatusById: (args: updateStatusParams) => void;
  updateNodeInheritanceById: (args: updateInheritanceParams) => void;
  setSelectedNodes: (nodes: ChartNodes) => void;
};

const WorkflowJobsFlowChart: ForwardRefRenderFunction<ChartExposedRef | undefined, Props> = (
  { workflowConfig, nodeType, side, selectable = true, onJobClick, onCanvasClick },
  parentRef,
) => {
  if (nodeType === 'fork' && !side) {
    console.error(
      "[WorkflowJobsFlowChart]: Detect that current type is FORK but side has't been assigned",
    );
  }
  const [chartInstance, setChartInstance] = useState<OnLoadParams>();
  const [elements, setElements] = useState<ChartElements>([]);
  // ☢️ WARNING: since we using react-flow hooks here,
  // an ReactFlowProvider is REQUIRED to wrap this component inside
  const jobNodes = (useStoreState((store) => store.nodes) as unknown) as ChartNodes;
  const setSelectedElements = useStoreActions((actions) => actions.setSelectedElements);

  // To decide if need to re-generate jobElements, look out that re-gen elements
  // will lead all nodes loose it's status!!💣
  //
  // Q: why not put workflowConfig directly as the dependent?
  // A: At workflowConfig's inner may contains variables' value
  // and will change during user configuring, but we do not want that lead
  // re-generate chart elements
  const workflowIdentifyString = workflowConfig.job_definitions
    .map((item) => item.name)
    .concat(workflowConfig.variables?.map((item) => item.name) || [])
    .join('|');

  useEffect(() => {
    const jobElements = convertToChartElements(
      {
        jobs: workflowConfig.job_definitions,
        globalVariables: workflowConfig.variables || [],
        side,
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
        nodeTypes={WorkflowJobNode}
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
    return nodeIds.some((id) => elements.find((item) => item.id === id)?.data?.inherit === false);
  }
  function updateNodeStatus(args: updateStatusParams) {
    if (!args.id) return;

    setElements((els) => {
      return (els as ChartElements).map((el) => {
        if (el.id === args.id) {
          el.data = {
            ...el.data,
            status: args.status,
          };
        }
        return el;
      });
    });
  }
  function updateNodeInheritance({ id, whetherInherit }: updateInheritanceParams) {
    if (nodeType !== 'fork' || !id) {
      return;
    }
    const nextElements = cloneDeep(elements as ChartNodes);
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

    target.data.inherit = whetherInherit;

    // Collect dependent chain
    const depsChainCollected: string[] = [];

    depsChainCollected.push(target?.id!);

    nextElements.forEach((item) => {
      if (!isNode(item)) return;

      const hasAnyDependentOnPrevs = item.data.raw.dependencies.find((dep) => {
        return depsChainCollected.includes(dep.source);
      });

      if (hasAnyDependentOnPrevs) {
        item.data.inherit = whetherInherit;

        depsChainCollected.push(item.id);
      }
    });

    setElements(nextElements);
  }
};

export default forwardRef(WorkflowJobsFlowChart);
