import { Elements, Node, XYPosition, Edge } from 'react-flow-renderer';
import { Job, JobExecutionDetalis, JobState } from 'typings/job';
import { isHead, isLast } from 'shared/array';
import { head, last } from 'lodash';

const TOP_OFFSET = 100;
const LEFT_OFFSET = 100;
export const NODE_WIDTH = 200;
export const NODE_HEIGHT = 80;
export const NODE_GAP = 30;

export enum JobNodeStatus {
  Pending,
  Processing,
  Warning,
  Success,
  Error,
}

export type JobColorsMark = 'blue' | 'green' | 'yellow' | 'magenta' | 'cyan';
export type JobRawData = Job & Partial<JobExecutionDetalis> & { mark?: JobColorsMark };

export type JobNodeData = {
  raw: JobRawData; // each jobs raw-config plus it's execution details if has
  index: number;
  isSource?: boolean;
  isTarget?: boolean;
  status: JobNodeStatus;
  values?: object;
  mark?: JobColorsMark;
};
export interface JobNode extends Node {
  data: JobNodeData;
}

export type JobNodeType = 'config' | 'execution';

export function convertJobsToElements(
  jobs: JobRawData[],
  options: { type: JobNodeType; selectable: boolean },
): any {
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
  let rowIdx = 0;
  const rowsComputed = jobs.reduce((rows: Array<JobNode[]>, job, jobIdx) => {
    if (shouldPutIntoNextRow()) {
      rowIdx++;
    }
    addANewRowIfNotExist();

    const node = createNode();

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

    function createNode(): JobNode {
      const status = job.state ? convertExecutionStateToStatus(job.state) : JobNodeStatus.Pending;

      return {
        id: getNodeIdByJob(job),
        data: { raw: job, index: jobIdx, status, mark: job.mark || undefined },
        position: { x: 0, y: 0 }, // position will be calculated in later step
        ...options,
      };
    }
  }, []);

  // 2. Calculate Node position & Generate Edges
  const jobsCountInMostBigRow = Math.max(...rowsComputed.map((r) => r.length));
  const maxWidth = getRowWidth(jobsCountInMostBigRow);
  const midlineX = maxWidth / 2 + LEFT_OFFSET;

  return rowsComputed.reduce((result, curRow, rowIdx) => {
    const isHeadRow = isHead(curRow, rowsComputed);
    const isLastRow = isLast(curRow, rowsComputed);

    curRow.forEach((node, nodeIdx) => {
      const position = getNodePosition({ nodesCount: curRow.length, rowIdx, nodeIdx, midlineX });

      Object.assign(node.position, position);

      if (!isHeadRow) {
        // Create Edges
        // NOTE: only rows not at head can have edge
        const prevRow = rowsComputed[rowIdx - 1];

        if (isHead(node, curRow)) {
          const source = head(prevRow)!;
          source.data.isSource = true;
          node.data.isTarget = true;
          result.push(createEdge(source, node));
        }

        if (isLast(node, curRow) && (prevRow.length > 1 || curRow.length > 1)) {
          const source = last(prevRow)!;
          source.data.isSource = true;
          node.data.isTarget = true;
          result.push(createEdge(source, node));
        }
      } else {
      }

      if (isLastRow) {
        // node.data.source
      }

      result.push(node);
    });
    return result;
  }, [] as Elements);
}

function getRowWidth(count: number) {
  return count * NODE_WIDTH + (count - 1) * NODE_GAP;
}

type GetPositionParams = { nodesCount: number; rowIdx: number; nodeIdx: number; midlineX: number };

function getNodePosition({ nodesCount, rowIdx, nodeIdx, midlineX }: GetPositionParams): XYPosition {
  const _1stNodeX = midlineX - (NODE_WIDTH * nodesCount) / 2 - ((nodesCount - 1) * NODE_GAP) / 2;
  const x = _1stNodeX + nodeIdx * (NODE_WIDTH + NODE_GAP);
  const y = TOP_OFFSET + rowIdx * (NODE_HEIGHT + NODE_GAP);

  return { x, y };
}

// We using the name of job as Node ID at present
export function getNodeIdByJob(job: Job) {
  return job.name;
}

function createEdge(source: JobNode, target: JobNode): Edge {
  return {
    id: `E|${source.id}-${target.id}`,
    source: source.id,
    target: target.id,
    type: 'smoothstep',
  };
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
