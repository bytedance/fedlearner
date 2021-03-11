import { Edge, Node } from 'react-flow-renderer';
import { JobExecutionDetalis, Job } from 'typings/job';
import { Variable } from 'typings/variable';

export enum ChartNodeStatus {
  Pending,
  Processing,
  Warning,
  Success,
  Error,
}

export type JobColorsMark = 'blue' | 'green' | 'yellow' | 'magenta' | 'cyan';

// Except for 'global', others all stand for a job node, i.e. 'config' is job config, 'fork' is job fork
export type ChartNodeType = 'config' | 'execution' | 'global' | 'fork';
export type TPLChartNodeType = 'tpl-config' | 'tpl-global';
export type AllNodeTypes = ChartNodeType | TPLChartNodeType;

/**
 * 1. At Workflow create stage, JobNodeRawData === Job or GlobalVariables
 * 2. At Workflow detail page, JobNodeRawData would contain JobExecutionDetalis and JobColorsMark additionally
 */
export type JobNodeRawData = Job &
  JobExecutionDetalis & {
    mark?: JobColorsMark;
    inherited?: boolean;
    k8sName?: string;
    uuid?: string; // uuid should exist when node on template canvas
  };

export type GlobalNodeRawData = { variables: Variable[]; name: string };

export type NodeData<R = JobNodeRawData> = {
  raw: R;
  index: number;
  status: ChartNodeStatus;
  isGlobal?: boolean;
  isSource?: boolean;
  isTarget?: boolean;
  mark?: JobColorsMark;
  rows?: { raw: JobNodeRawData; isGlobal?: boolean }[][];
  inherit?: boolean; // When forking workflow, some node's result can be inherit
  side?: string; // Assign it while forking workflow, let node tell which side it belongs
};
export interface JobNode extends Node {
  data: NodeData;
  type: AllNodeTypes;
}
export interface GlobalConfigNode extends Node {
  data: NodeData<GlobalNodeRawData>;
  type: AllNodeTypes;
}
export type ChartNode = JobNode | GlobalConfigNode;
export type ChartNodes = ChartNode[];
export type ChartElements = (GlobalConfigNode | JobNode | Edge)[];
