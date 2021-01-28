import { Node, XYPosition, Edge } from 'react-flow-renderer';
import { Job, JobExecutionDetalis, JobState, JobType } from 'typings/job';
import { isHead, isLast } from 'shared/array';
import { head, isEmpty, isNil, last } from 'lodash';
import { Variable } from 'typings/workflow';
import i18n from 'i18n';

const TOP_OFFSET = 100;
const LEFT_OFFSET = 100;

export const NODE_WIDTH = 200;
export const NODE_HEIGHT = 80;
export const GLOBAL_CONFIG_NODE_SIZE = 120;
export const NODE_GAP = 30;

export enum JobNodeStatus {
  Pending,
  Processing,
  Warning,
  Success,
  Error,
}

export type JobNodeType = 'config' | 'execution' | 'global';
export type JobColorsMark = 'blue' | 'green' | 'yellow' | 'magenta' | 'cyan';
/**
 * 1. At Workflow create stage, JobNodeRawData === Job only
 * 2. At Workflow detail page, JobNodeRawData would contain JobExecutionDetalis and JobColorsMark additionally
 */
export type JobNodeRawData = Job & Partial<JobExecutionDetalis> & { mark?: JobColorsMark };

export type JobNodeData = {
  raw: JobNodeRawData; // each jobs raw-config plus it's execution details if has
  index: number;
  isSource?: boolean;
  isTarget?: boolean;
  status: JobNodeStatus;
  // values?: object;
  mark?: JobColorsMark;
};
export interface JobNode extends Node {
  data: JobNodeData;
  type: JobNodeType;
}
export interface GlobalConfigNode extends Node {
  data: JobNodeData & { raw: { variables: Variable[] } };
  type: JobNodeType;
}
export type JobElements = (GlobalConfigNode | JobNode | Edge)[];

/**
 * Turn job defintitions to flow elements (include edges),
 * NOTE: globalVariables is considered as a Node as well
 */
export function convertJobsToElements(
  { jobs, globalVariables }: { jobs: JobNodeRawData[]; globalVariables?: Variable[] },
  options: { type: JobNodeType; selectable: boolean },
): JobElements {
  const hasGlobalVars = !isNil(globalVariables) && !isEmpty(globalVariables);
  // 1. Group Jobs to rows by dependiences
  // e.g. Say we have jobs like [1, 2, 3, 4, 5] in which 2,3,4 is depend on 1, 5 depend on 2,3,4
  // we need to render jobs like charts below,
  //
  // row-1        █1█
  //          ╭┈┈┈ ↓ ┈┈┈╮
  // row-2   █2█  █3█  █4█
  //          ╰┈┈┈ ↓ ┈┈┈╯
  // row-3        █5█
  //
  // thus the processed rows will looks like [[1], [2, 3, 4], [5]]
  const rows: Array<(JobNode | GlobalConfigNode)[]> = [];
  let rowIdx = 0;

  // If global variables existing, always put it into first row
  if (hasGlobalVars) {
    const globalNode = _createGlobalConfigNode(globalVariables!);
    rows.push([globalNode]);
    rowIdx++;
  }

  const rowsComputed = jobs.reduce((rows, job, jobIdx) => {
    if (shouldPutIntoNextRow()) {
      rowIdx++;
    }
    addANewRowIfNotExist();

    const node = _createJobNode({ job, index: jobIdx, options, hasGlobalVars });

    pushToCurrentRow(node);

    return rows;

    /**
     * When the Job depend on some Jobs before it (Pre-jobs),
     * plus the Pre-job(s) ARE on the current row,
     * then we should put it into next row
     */
    function shouldPutIntoNextRow() {
      if (!job.dependencies) return false;

      return job.dependencies.some((dep) => {
        return rows[rowIdx].some((item) => item.id === dep.source);
      });
    }
    function pushToCurrentRow(node: JobNode) {
      rows[rowIdx].push(node);
    }
    function addANewRowIfNotExist() {
      if (!rows[rowIdx]) {
        rows[rowIdx] = [];
      }
    }
  }, rows);

  // 2. Calculate Node position & Generate Edges
  const jobsCountInMostBigRow = Math.max(...rowsComputed.map((r) => r.length));
  const maxWidth = _getRowWidth(jobsCountInMostBigRow);
  const midlineX = maxWidth / 2 + LEFT_OFFSET;

  return rowsComputed.reduce((result, curRow, rowIdx) => {
    const isHeadRow = isHead(curRow, rowsComputed);

    curRow.forEach((node, nodeIdx) => {
      const position = _getNodePosition({
        nodesCount: curRow.length,
        rowIdx,
        nodeIdx,
        midlineX,
        type: node.type! as JobNodeType,
      });

      Object.assign(node.position, position);

      if (!isHeadRow) {
        // Create Edges
        // NOTE: only rows not at head can have edge
        const prevRow = rowsComputed[rowIdx - 1];

        if (isHead(node, curRow)) {
          const source = head(prevRow)!;
          source.data.isSource = true;
          node.data.isTarget = true;
          result.push(_createEdge(source, node));
        }

        if (isLast(node, curRow) && (prevRow.length > 1 || curRow.length > 1)) {
          const source = last(prevRow)!;
          source.data.isSource = true;
          node.data.isTarget = true;
          result.push(_createEdge(source, node));
        }
      }

      result.push(node);
    });
    return result;
  }, [] as JobElements);
}

export function convertExecutionStateToStatus(state: JobState): JobNodeStatus {
  return {
    [JobState.NEW]: JobNodeStatus.Pending,
    [JobState.WAITING]: JobNodeStatus.Pending,
    [JobState.RUNNING]: JobNodeStatus.Processing,
    [JobState.COMPLETE]: JobNodeStatus.Success,
    [JobState.STOPPED]: JobNodeStatus.Error,
    [JobState.FAILED]: JobNodeStatus.Warning,
    [JobState.INVALID]: JobNodeStatus.Warning,
  }[state];
}

// We using the name of job as Node ID at present
export function getNodeIdByJob(job: Job) {
  return job.name;
}

// --------------- Private helpers  ---------------

function _createGlobalConfigNode(variables: Variable[]): GlobalConfigNode {
  const name = i18n.t('workflow.label_global_config');

  return {
    id: name,
    type: 'global',
    data: {
      raw: ({
        variables,
        name,
        dependencies: [],
      } as unknown) as JobNodeRawData,
      index: 0,
      status: JobNodeStatus.Pending,
    },
    position: { x: 0, y: 0 },
  };
}

function _createJobNode(params: {
  job: JobNodeRawData;
  index: number;
  options: any;
  hasGlobalVars?: boolean;
}): JobNode {
  const { job, index, options, hasGlobalVars } = params;
  const status = job.state ? convertExecutionStateToStatus(job.state) : JobNodeStatus.Pending;

  return {
    id: getNodeIdByJob(job),
    data: {
      raw: job,
      index: hasGlobalVars ? index + 1 : index, // if have global variables, all nodes should be put behind it
      mark: job.mark || undefined,
      status,
    },
    position: { x: 0, y: 0 }, // position will be calculated in later step
    ...options,
  };
}

function _createEdge(source: JobNode, target: JobNode): Edge {
  return {
    id: `E|${source.id}-${target.id}`,
    source: source.id,
    target: target.id,
    type: 'smoothstep',
  };
}

function _getRowWidth(count: number) {
  return count * NODE_WIDTH + (count - 1) * NODE_GAP;
}

type GetPositionParams = {
  nodesCount: number;
  rowIdx: number;
  nodeIdx: number;
  midlineX: number;
  type: JobNodeType;
};
function _getNodePosition({
  nodesCount,
  rowIdx,
  nodeIdx,
  midlineX,
  type,
}: GetPositionParams): XYPosition {
  const isGlobalNode = type === 'global';
  const _1stNodeX = midlineX - (NODE_WIDTH * nodesCount) / 2 - ((nodesCount - 1) * NODE_GAP) / 2;
  let x = _1stNodeX + nodeIdx * (NODE_WIDTH + NODE_GAP);
  const y =
    TOP_OFFSET +
    (isGlobalNode
      ? (NODE_HEIGHT - GLOBAL_CONFIG_NODE_SIZE) / 2
      : rowIdx * (NODE_HEIGHT + NODE_GAP));

  if (type === 'global') {
    x += (NODE_WIDTH - GLOBAL_CONFIG_NODE_SIZE) / 2;
  }

  return { x, y };
}
