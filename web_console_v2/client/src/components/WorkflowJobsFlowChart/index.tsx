import React, { FC, useEffect, useState } from 'react';
import WorkflowJobNode from './WorkflowJobNode';
import { JobNodeType, JobRawData } from './helpers';
import styled from 'styled-components';
import ReactFlow, {
  Background,
  BackgroundVariant,
  isNode,
  OnLoadParams,
  FlowElement,
} from 'react-flow-renderer';
import { convertJobsToElements, JobNode, JobNodeStatus } from './helpers';

import PubSub from 'pubsub-js';
import { useSubscribe } from 'hooks';
import { Job, JobExecutionDetalis } from 'typings/job';

const Container = styled.div`
  position: relative;
  /* TODO: remove the hard-coded 48px of chart header */
  height: ${(props: any) => `calc(100% - ${props.top || '0px'} - 48px)`};
  background-color: var(--gray1);

  /* react flow styles override */
  .react-flow__node {
    border-radius: 4px;
    font-size: 1em;
    border-color: transparent;
    text-align: initial;
    border: 1px solid white;
    background-color: white;
    cursor: initial;

    &-execution,
    &-config {
      &.selected {
        border-color: var(--primaryColor);
        box-shadow: none;
        background-color: #f2f6ff;
      }
    }

    &.selectable {
      cursor: pointer;

      &:hover {
        box-shadow: 0px 4px 10px #e0e0e0;
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
`;
// Internal pub-sub channels, needless to put in any shared file
const CHANNELS = {
  update_node_status: 'workflow_job_flow_chart.update_node_status',
};

type Props = {
  jobs: (Job | JobExecutionDetalis)[];
  type: JobNodeType;
  selectable?: boolean;
  onJobClick?: (node: JobNode) => void;
  onCanvasClick?: () => void;
};

const WorkflowJobsFlowChart: FC<Props> = ({
  jobs,
  type,
  selectable = true,
  onJobClick,
  onCanvasClick,
}) => {
  const [elements, setElements] = useState<FlowElement[]>([]);

  useEffect(() => {
    const eles = convertJobsToElements(jobs as JobRawData[], { type, selectable });
    setElements(eles);
  }, [jobs, type, selectable]);

  useSubscribe(
    CHANNELS.update_node_status,
    (_: string, arg: { id: string; status: JobNodeStatus }) => {
      updateNodeStatus(arg);
    },
  );

  return (
    <Container>
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
      </ReactFlow>
    </Container>
  );

  function onElementsClick(element: FlowElement) {
    if (isNode(element)) {
      onJobClick && onJobClick(element as JobNode);
    }
  }
  function onLoad(_reactFlowInstance: OnLoadParams) {
    _reactFlowInstance!.fitView({ padding: 2 });
  }
  function updateNodeStatus(arg: { id: string; status: JobNodeStatus }) {
    setElements((els) => {
      return els.map((el) => {
        if (el.id === arg.id) {
          el.data = {
            ...el.data,
            status: arg.status,
          };
        }
        return el;
      });
    });
  }
};

export function updateNodeStatusById(arg: { id: string; status: JobNodeStatus }) {
  PubSub.publish(CHANNELS.update_node_status, arg);
}

export default WorkflowJobsFlowChart;
