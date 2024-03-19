import React, {
  useEffect,
  useState,
  ForwardRefRenderFunction,
  forwardRef,
  useImperativeHandle,
  useRef,
} from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  isNode,
  OnLoadParams,
  FlowElement,
  useStoreActions,
  Controls,
  Node,
} from 'react-flow-renderer';
import {
  ChartElements,
  ChartNodeStatus,
  JobNodeRawData,
} from 'components/WorkflowJobsCanvas/types';
import { Container } from 'components/WorkflowJobsCanvas/elements';
import { JobNodeRawDataSlim, WorkflowTemplateForm } from 'stores/template';
import { Variable } from 'typings/variable';
import {
  ConvertParams,
  convertToChartElements,
  RawDataRows,
  RawDataCol,
} from 'components/WorkflowJobsCanvas/helpers';
import GlobalConfigNode from 'components/WorkflowJobsCanvas/JobNodes/GlobalConfigNode';
import TemplateConfigNode from './TemplateConfigNode';
import { TPL_GLOBAL_NODE_UUID } from 'views/WorkflowTemplates/TemplateForm/stores';

type Props = {
  isEdit?: boolean;
  isCheck?: boolean;
  template: WorkflowTemplateForm;
  onCanvasClick?: any;
  onNodeClick?: any;
};
type UpdateStatusParams = {
  id: string;
  status: ChartNodeStatus;
};

export type ExposedRef = {
  chartInstance: OnLoadParams;
  setSelectedNodes(nodes: Node[]): any;
  updateNodeStatusById(params: UpdateStatusParams): any;
};

const TemplateCanvas: ForwardRefRenderFunction<ExposedRef, Props> = (
  { template, onCanvasClick, onNodeClick, isEdit, isCheck },
  parentRef,
) => {
  const isInitialConvert = useRef(true);

  const [chartInstance, setChartInstance] = useState<OnLoadParams>();
  const [elements, setElements] = useState<ChartElements>([]);

  // ☢️ WARNING: since we using react-flow hooks here,
  // an ReactFlowProvider is REQUIRED to wrap this component inside
  const setSelectedNodes = useStoreActions((actions) => actions.setSelectedElements);

  const templateIdentifyString = template.config.job_definitions
    .map((item, index) => index + item.uuid + (item.mark || ''))
    .join('|');

  useEffect(() => {
    const jobElements = convertToChartElements(
      {
        jobs: template.config.job_definitions as any,
        variables: template.config.variables || [],
        data: {
          /**
           * Assign node status by current context
           * 1. If the node has status before, just reuse it
           * 2. If the node is new created, set to Pending
           * 3. If is edit-mode plus first time convert, all node should be Success by default
           */
          status({ raw, isGlobal }: RawDataCol) {
            const node = elements.find(
              (node) =>
                node.id === (isGlobal ? TPL_GLOBAL_NODE_UUID : (raw as JobNodeRawDataSlim).uuid),
            );

            if (node) {
              return node.data.status;
            }

            return isEdit && isInitialConvert.current
              ? ChartNodeStatus.Success
              : ChartNodeStatus.Pending;
          },
        },
      },
      { type: 'tpl-config', selectable: true },
      {
        createGlobal: _createTPLGlobalNode,
        createJob: _createTPLJobNode,
        groupRows: groupByUuidDeps,
      },
    );

    setElements(jobElements);
    // Set isInitialConvert to false
    if (isInitialConvert.current) {
      isInitialConvert.current = false;
    }
    // eslint-disable-next-line
  }, [templateIdentifyString]);

  useImperativeHandle(parentRef, () => {
    return {
      chartInstance: chartInstance!,
      setSelectedNodes,
      updateNodeStatusById: updateNodeStatus,
    };
  });

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
        defaultZoom={1}
        nodeTypes={{
          'tpl-config': TemplateConfigNode,
          'tpl-global': GlobalConfigNode,
        }}
      >
        <Background variant={BackgroundVariant.Dots} gap={12} size={1} color="#E1E6ED" />
        <Controls showZoom={false} showInteractive={false} />
      </ReactFlow>
    </Container>
  );

  function onLoad(_reactFlowInstance: OnLoadParams) {
    setChartInstance(_reactFlowInstance);

    // Fit view at next tick
    setImmediate(() => {
      _reactFlowInstance!.fitView();
    });
  }
  function onElementsClick(element: FlowElement) {
    if (isNode(element)) {
      onNodeClick && onNodeClick(element);
    }
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
};

function _createTPLGlobalNode(_: Variable[], data: any, options: any) {
  const name = '全局配置';

  return {
    id: TPL_GLOBAL_NODE_UUID,
    data: {
      raw: {
        variables: [],
        name,
      },
      status: ChartNodeStatus.Pending,
      isGlobal: true,
      ...data,
    },
    position: { x: 0, y: 0 },
    ...options,
    // Overwrite options.type passed through convertToChartElements
    type: 'tpl-global',
  };
}

function _createTPLJobNode(job: JobNodeRawDataSlim, data: any, options: any) {
  return {
    id: job.uuid,
    data: {
      raw: job,
      status: ChartNodeStatus.Pending,
      mark: job.mark,
      ...data,
    },
    position: { x: 0, y: 0 },
    ...options,
  };
}

export function groupByUuidDeps(params: ConvertParams) {
  const { jobs, variables } = params;

  const rows: RawDataRows = [];
  let rowIdx = 0;

  // Always put global node into first row
  rows.push([{ raw: variables, isGlobal: true }]);
  rowIdx++;

  return jobs.reduce((rows, job) => {
    if (shouldPutIntoNextRow()) {
      rowIdx++;
    }

    addANewRowIfNotExist();

    rows[rowIdx].push({ raw: job });

    return rows;

    function shouldPutIntoNextRow() {
      if (!job.dependencies) return false;

      return job.dependencies.some((dep) => {
        return rows[rowIdx].some((item) => {
          const raw = item.raw as JobNodeRawData;

          return dep.source === raw.uuid;
        });
      });
    }
    function addANewRowIfNotExist() {
      if (!rows[rowIdx]) {
        rows[rowIdx] = [];
      }
    }
  }, rows);
}

export default forwardRef(TemplateCanvas);
