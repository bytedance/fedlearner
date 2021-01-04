import { Elements, Node, XYPosition, Edge } from 'react-flow-renderer'
import { Job } from 'typings/workflow'
import { isHead, isLast } from 'shared/array'
import { head, last } from 'lodash'

const TOP_OFFSET = 100
const LEFT_OFFSET = 30
export const NODE_WIDTH = 200
export const NODE_HEIGHT = 80
export const NODE_GAP = 30

export enum JobNodeStatus {
  Pending,
  Configuring,
  Unfinished,
  Completed,
}

export type JobNodeData = {
  raw: Job // each jobs raw-config
  index: number
  isSource?: boolean
  isTarget?: boolean
  status: JobNodeStatus
  values?: object
}
export interface JobNode extends Node {
  data: JobNodeData
}

export function convertJobsToElements(jobs: Job[]): any {
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
  let rowIdx = 0
  const rowsComputed = jobs.reduce((rows: Array<JobNode[]>, job, jobIdx) => {
    if (shouldPutIntoNextRow()) {
      rowIdx++
    }
    addANewRowIfNotExist()

    const node = createNode()

    pushToCurrentRow(node)

    return rows

    /**
     * When the Job depend on some Jobs before it (Pre-jobs),
     * plus the Pre-job(s) ARE on the current row,
     * then we should put it into next row
     */
    function shouldPutIntoNextRow() {
      if (!job.dependencies) return false

      return job.dependencies.some((dep) => {
        return rows[rowIdx].some((item) => item.id === dep.source)
      })
    }
    function pushToCurrentRow(node: JobNode) {
      rows[rowIdx].push(node)
    }
    function addANewRowIfNotExist() {
      if (!rows[rowIdx]) {
        rows[rowIdx] = []
      }
    }

    function createNode(): JobNode {
      return {
        id: getNodeIdByJob(job),
        data: { raw: job, index: jobIdx, status: JobNodeStatus.Pending },
        position: { x: 0, y: 0 }, // position will be calculated in later step
      }
    }
  }, [])

  // 2. Calculate Node position & Generate Edges
  const jobsCountInMostBigRow = Math.max(...rowsComputed.map((r) => r.length))
  const maxWidth = getRowWidth(jobsCountInMostBigRow)
  const midlineX = maxWidth / 2 + LEFT_OFFSET

  return rowsComputed.reduce((result, curRow, rowIdx) => {
    const isHeadRow = isHead(curRow, rowsComputed)
    const isLastRow = isLast(curRow, rowsComputed)

    curRow.forEach((node, nodeIdx) => {
      const position = getNodePosition({ nodesCount: curRow.length, rowIdx, nodeIdx, midlineX })

      Object.assign(node.position, position)

      if (!isHeadRow) {
        // Create Edges
        // NOTE: only rows not at head can have edge
        const prevRow = rowsComputed[rowIdx - 1]

        if (isHead(node, curRow)) {
          const source = head(prevRow)!
          source.data.isSource = true
          node.data.isTarget = true
          result.push(createEdge(source, node))
        }

        if (isLast(node, curRow) && (prevRow.length > 1 || curRow.length > 1)) {
          const source = last(prevRow)!
          source.data.isSource = true
          node.data.isTarget = true
          result.push(createEdge(source, node))
        }
      } else {
      }

      if (isLastRow) {
        // node.data.source
      }

      result.push(node)
    })
    return result
  }, [] as Elements)
}

function getRowWidth(count: number) {
  return count * NODE_WIDTH + (count - 1) * NODE_GAP
}

type GetPositionParams = { nodesCount: number; rowIdx: number; nodeIdx: number; midlineX: number }

function getNodePosition({ nodesCount, rowIdx, nodeIdx, midlineX }: GetPositionParams): XYPosition {
  const _1stNodeX = midlineX - (NODE_WIDTH * nodesCount) / 2 - ((nodesCount - 1) * NODE_GAP) / 2
  const x = _1stNodeX + nodeIdx * (NODE_WIDTH + NODE_GAP)
  const y = TOP_OFFSET + rowIdx * (NODE_HEIGHT + NODE_GAP)

  return { x, y }
}

// We using the name of job as Node ID at present
export function getNodeIdByJob(job: Job) {
  return job.name
}

function createEdge(source: JobNode, target: JobNode): Edge {
  return {
    id: `E|${source.id}-${target.id}`,
    source: source.id,
    target: target.id,
    type: 'smoothstep',
  }
}
