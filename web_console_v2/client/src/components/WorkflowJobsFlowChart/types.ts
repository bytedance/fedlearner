import { Edge, Node } from 'react-flow-renderer';
import { JobExecutionDetalis, Job } from 'typings/job';

export enum ChartNodeStatus {
  Pending,
  Processing,
  Warning,
  Success,
  Error,
}

export type JobColorsMark = 'blue' | 'green' | 'yellow' | 'magenta' | 'cyan';

export type ChartNodeType = 'config' | 'execution' | 'global' | 'fork';

/**
 * 1. At Workflow create stage, NodeDataRaw === Job or GlobalVariables
 * 2. At Workflow detail page, NodeDataRaw would contain JobExecutionDetalis and JobColorsMark additionally
 */
export type NodeDataRaw = Job &
  Partial<JobExecutionDetalis> & { mark?: JobColorsMark; inherited?: boolean };

export type NodeData = {
  raw: NodeDataRaw;
  index: number;
  isSource?: boolean;
  isTarget?: boolean;
  status: ChartNodeStatus;
  mark?: JobColorsMark;
  inherit?: boolean; // When forking workflow, some node's result can be inherit
  side?: string; // Assign it while forking workflow, let node tell which side it belongs
};
export interface JobNode extends Node {
  data: NodeData;
  type: ChartNodeType;
}
export interface GlobalConfigNode extends Node {
  data: NodeData;
  type: ChartNodeType;
}
export type ChartNode = JobNode | GlobalConfigNode;
export type ChartNodes = ChartNode[];
export type ChartElements = (GlobalConfigNode | JobNode | Edge)[];
