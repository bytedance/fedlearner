import React, { FC } from 'react';

import { formatTimestamp } from 'shared/date';

import Table from 'components/Table';
import MoreActions from 'components/MoreActions';

import { Model } from 'typings/modelCenter';
import { generatePath, useHistory } from 'react-router';
import routes from 'views/ModelCenter/routes';
import CONSTANTS from 'shared/constants';
import AlgorithmType from 'components/AlgorithmType';
import { EnumAlgorithmProjectType } from 'typings/algorithm';

type ColumnsGetterOptions = {
  onDeleteClick?: (model: Model) => void;
  onEditClick?: (model: Model) => void;
  onModelSourceClick?: (model: Model, to: string) => void;
  withoutActions?: boolean;
  isOldModelCenter?: boolean;
};

export const getTableColumns = (options: ColumnsGetterOptions) => {
  const cols = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      // TODO: Click name go to detail page
    },
    {
      title: '模型类型',
      dataIndex: 'algorithm_type',
      key: 'algorithm_type',
      width: 150,
      render: (type: EnumAlgorithmProjectType) => {
        return <AlgorithmType type={type} />;
      },
    },
    {
      title: '模型来源',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 200,
      render: (value: any, record: Model) => {
        const {
          job_id,
          model_job_id,
          group_id,
          workflow_id,
          job_name,
          model_job_name,
          workflow_name,
        } = record;

        let to = '';
        let displayText = '';
        if (job_id && workflow_id && job_name && workflow_name) {
          to = `/workflow-center/workflows/${workflow_id}`;
          displayText = `${workflow_name}工作流-${job_name}任务`;
        }
        if (model_job_id && group_id && model_job_name) {
          to = options.isOldModelCenter
            ? `/model-center/model-management/model-set/${group_id}`
            : generatePath(routes.ModelTrainDetail, {
                id: group_id,
              });
          displayText = `${model_job_name}训练任务`;
        }

        return (
          <button
            className="custom-text-button"
            style={{ textAlign: 'left' }}
            onClick={() => {
              options?.onModelSourceClick?.(record, to);
            }}
          >
            {displayText}
          </button>
        );
      },
    },
    {
      title: '模型描述',
      dataIndex: 'comment',
      key: 'comment',
      width: 200,
      render: (comment: string) => comment || CONSTANTS.EMPTY_PLACEHOLDER,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: number) => <div>{formatTimestamp(date)}</div>,
      sorter: (a: Model, b: Model) => a.created_at - b.created_at,
    },
  ];
  if (!options.withoutActions) {
    cols.push({
      title: '操作',
      dataIndex: 'operation',
      key: 'operation',
      fixed: 'right',
      width: 100,
      render: (_: number, record: Model) => {
        return (
          <>
            <MoreActions
              actionList={[
                {
                  label: '编辑',
                  onClick: () => {
                    options?.onEditClick?.(record);
                  },
                },
                {
                  label: '删除',
                  onClick: () => {
                    options?.onDeleteClick?.(record);
                  },
                  danger: true,
                },
              ]}
            />
          </>
        );
      },
    } as any);
  }

  return cols;
};

type Props = {
  loading: boolean;
  isOldModelCenter: boolean;
  dataSource: any[];
  onDeleteClick?: (record: Model) => void;
  onEditClick?: (record: Model) => void;
  onShowSizeChange?: (current: number, size: number) => void;
  onPageChange?: (page: number, pageSize: number) => void;
};
const ModelTable: FC<Props> = ({
  loading,
  isOldModelCenter = false,
  dataSource,
  onDeleteClick,
  onEditClick,
  onShowSizeChange,
  onPageChange,
}) => {
  const history = useHistory();
  return (
    <>
      <Table
        rowKey="id"
        scroll={{ x: '100%' }}
        loading={loading}
        data={dataSource}
        columns={getTableColumns({
          isOldModelCenter,
          onDeleteClick,
          onEditClick,
          onModelSourceClick: (model: Model, to: string) => {
            if (to) {
              history.push(to);
            }
          },
        })}
        onShowSizeChange={onShowSizeChange}
        onPageChange={onPageChange}
      />
    </>
  );
};

export default ModelTable;
