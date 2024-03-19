import { Edge, Node } from 'react-flow-renderer';
import { JobExecutionDetalis, Job } from 'typings/job';
import { Variable } from 'typings/variable';

export enum ChartNodeStatus {
  Pending,
  Processing,
  Validating,
  Warning,
  Success,
  Error,
}

export type JobColorsMark = 'blue' | 'green' | 'yellow' | 'magenta' | 'cyan' | 'red' | 'purple';

// Except for 'global', others all stand for a job node, i.e. 'config' is job config, 'fork' is job fork
export type ChartNodeType = 'config' | 'execution' | 'global' | 'fork' | 'edit';
export type TPLChartNodeType = 'tpl-config' | 'tpl-global';
export type AllNodeTypes = ChartNodeType | TPLChartNodeType;

/**
 * 1. At Workflow create stage, JobNodeRawData === Job or GlobalVariables
 * 2. At Workflow detail page, JobNodeRawData would contain JobExecutionDetalis and JobColorsMark additionally
 */
export type JobNodeRawData = Job &
  JobExecutionDetalis & {
    mark?: JobColorsMark;
    /** whether the job has been reused, can be infered by workflow.create_job_flags */
    reused?: boolean;
    /** whether the job has been disabled, can be infered by workflow.create_job_flags as well */
    disabled?: boolean;
    /** the job name under k8s environment, consist with ${workflow-uuid}-${job-def-name}  */
    k8sName?: string;
    /** ! uuid will only exist in Template Canvas */
    uuid?: string;
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
  disabled?: boolean; // whether DISABLE the job
  /** When forking workflow, some node's result can be inherited, a.k.a: reused */
  inherited?: boolean;
  /** Assign it while forking workflow, let node tell which side it belongs */
  side?: string;
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
