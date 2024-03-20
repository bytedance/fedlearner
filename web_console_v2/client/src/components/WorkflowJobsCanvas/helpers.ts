import { XYPosition, Edge } from 'react-flow-renderer';
import { Job, JobState } from 'typings/job';
import { isHead, isLast } from 'shared/array';
import { Dictionary, head, isEmpty, isNil, last } from 'lodash';
import { Variable } from 'typings/variable';
import i18n from 'i18n';
import {
  JobNodeRawData,
  AllNodeTypes,
  ChartNode,
  ChartElements,
  ChartNodeStatus,
  JobNode,
  GlobalConfigNode,
} from './types';

export const NODE_WIDTH = 200;
export const NODE_HEIGHT = 80;
export const GLOBAL_CONFIG_NODE_SIZE = 120;
export const NODE_GAP = 40;

export type ConvertParams = {
  /** Job defintions & Job exe details & some meta-infos such as reused */
  jobs: JobNodeRawData[];
  /** a.k.a. worlflow global settings */
  variables: Variable[];
  /** Extra data pass to react-flow node data */
  data: Dictionary<any>;
};

export type NodeOptions = {
  type: AllNodeTypes;
  selectable: boolean;
};

export type RawDataCol = { raw: JobNodeRawData | Variable[]; isGlobal?: boolean };
export type RawDataRows = Array<RawDataCol[]>;

type ExtraNodeData = {
  index: number;
  status: ChartNodeStatus;
  [key: string]: any;
};

type NodeProcessors = {
  createJob(job: any, extraData: ExtraNodeData, options: NodeOptions): JobNode;
  createGlobal(variables: any, extraData: ExtraNodeData, options: NodeOptions): GlobalConfigNode;
  groupRows(params: ConvertParams): RawDataRows;
};

/**
 * Turn workflow config schema to react-flow elements (will include edges),
 * NOTE: globalVariables is considered as a Node as well
 */
export function convertToChartElements(
  params: ConvertParams,
  options: NodeOptions,
  processors: NodeProcessors = {
    createGlobal: _createGlobalNode,
    createJob: _createJobNode,
    groupRows: groupByDependencies,
  },
): ChartElements {
  /**
   * 1. Group jobs/global-vars into rows
   */
  const rows = processors.groupRows(params);

  /**
   * 2. Turn each col-item in rows to chart node
   */
  let selfIncreaseIndex = 0;
  const nodesRows = rows.map((row) => {
    return row.map((col) => {
      const extraData = { index: selfIncreaseIndex++, rows } as any;

      // Process params.data
      Object.entries(params.data || {}).forEach(([key, value]) => {
        if (typeof value === 'function') {
          return (extraData[key] = value(col));
        }

        extraData[key] = value;
      });

      if (col.isGlobal) {
        return processors.createGlobal(col.raw as Variable[], extraData, options);
      }
      return processors.createJob(col.raw as JobNodeRawData, extraData, options);
    });
  });

  /**
   * 3. Calculate Node position & Generate Edges
   */
  const jobsCountInBiggestRow = Math.max(...nodesRows.map((r) => r.length));
  const maxWidth = _getRowWidth(jobsCountInBiggestRow);
  const midlineX = maxWidth / 2;

  return nodesRows.reduce((result, curRow, rowIdx) => {
    const isHeadRow = isHead(curRow, nodesRows);

    curRow.forEach((node, nodeIdx) => {
      const position = _getNodePosition({
        nodesCount: curRow.length,
        rowIdx,
        nodeIdx,
        midlineX,
        isGlobal: node.data.isGlobal,
      });

      Object.assign(node.position, position);

      if (!isHeadRow) {
        // Create Edges
        // NOTE: only rows not at head can have edge
        const prevRow = nodesRows[rowIdx - 1];

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
  }, [] as ChartElements);
}

export function groupByDependencies(params: ConvertParams) {
  const { jobs, variables } = params;
  const hasGlobalVars = !isNil(variables) && !isEmpty(variables);

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
  const rows: RawDataRows = [];
  let rowIdx = 0;

  // If global variables existing, always put it into first row
  if (hasGlobalVars) {
    rows.push([{ raw: variables!, isGlobal: true }]);
    rowIdx++;
  }

  return jobs.reduce((rows, job) => {
    if (shouldPutIntoNextRow()) {
      rowIdx++;
    }

    addANewRowIfNotExist();

    rows[rowIdx].push({ raw: job });

    return rows;

    /**
     * When the Job depend on some Jobs before it (Pre-jobs),
     * plus the Pre-job(s) ARE on the current row,
     * then we should put it into next row
     */
    function shouldPutIntoNextRow() {
      if (!job.dependencies) return false;

      try {
        return job.dependencies.some((dep) => {
          return rows[rowIdx].some((item) => {
            const raw = item.raw as JobNodeRawData;

            return dep.source === raw.name;
          });
        });
      } catch (error) {
        return false;
      }
    }
    function addANewRowIfNotExist() {
      if (!rows[rowIdx]) {
        rows[rowIdx] = [];
      }
    }
  }, rows);
}

/* istanbul ignore next */
export function convertExecutionStateToStatus(state: JobState): ChartNodeStatus {
  return {
    [JobState.NEW]: ChartNodeStatus.Pending,
    [JobState.WAITING]: ChartNodeStatus.Pending,
    [JobState.RUNNING]: ChartNodeStatus.Processing,
    [JobState.STARTED]: ChartNodeStatus.Processing,
    [JobState.COMPLETED]: ChartNodeStatus.Success,
    [JobState.STOPPED]: ChartNodeStatus.Error,
    [JobState.FAILED]: ChartNodeStatus.Warning,
    [JobState.INVALID]: ChartNodeStatus.Warning,
  }[state];
}

// We using the name of job as Node ID at present
export function getNodeIdByJob(job: Job) {
  return job.name;
}

// --------------- Private helpers  ---------------

function _createGlobalNode(
  variables: Variable[],
  extraData: ExtraNodeData,
  options: NodeOptions,
): GlobalConfigNode {
  const name = i18n.t('workflow.label_global_config');
  const { type, ...restOptions } = options;

  return {
    id: name,
    type: 'global',
    ...restOptions,
    data: {
      raw: {
        variables,
        name,
      },
      isGlobal: true,
      ...extraData,
    },
    position: { x: 0, y: 0 },
  };
}

function _createJobNode(
  job: JobNodeRawData,
  extraData: ExtraNodeData,
  options: NodeOptions,
): JobNode {
  const isFork = options?.type === 'fork';

  return {
    id: getNodeIdByJob(job),
    ...options,
    data: {
      raw: job,
      ...extraData,
      mark: job.mark || undefined,
      inherited: isFork ? false : undefined, // under fork mode defaults to false
    },
    position: { x: 0, y: 0 }, // position will be calculated in later step
  };
}

function _createEdge(source: ChartNode, target: ChartNode): Edge {
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
  isGlobal?: boolean;
};

function _getNodePosition({
  nodesCount,
  rowIdx,
  nodeIdx,
  midlineX,
  isGlobal,
}: GetPositionParams): XYPosition {
  const _1stNodeX = midlineX - (NODE_WIDTH * nodesCount) / 2 - ((nodesCount - 1) * NODE_GAP) / 2;
  let x = _1stNodeX + nodeIdx * (NODE_WIDTH + NODE_GAP);

  const y = isGlobal
    ? (NODE_HEIGHT - GLOBAL_CONFIG_NODE_SIZE) / 1.5
    : rowIdx * (NODE_HEIGHT + NODE_GAP);

  if (isGlobal) {
    x += (NODE_WIDTH - GLOBAL_CONFIG_NODE_SIZE) / 2;
  }

  return { x, y };
}
