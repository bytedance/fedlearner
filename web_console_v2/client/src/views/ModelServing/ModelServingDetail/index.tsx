import React, { FC, useMemo } from 'react';
import { cloneDeep } from 'lodash-es';
import { useHistory, useParams } from 'react-router';
import { useQuery } from 'react-query';
import { useUrlState, useGetCurrentProjectId } from 'hooks';

import { fetchModelServingDetail_new, deleteModelServing_new } from 'services/modelServing';
import { formatTimestamp } from 'shared/date';
import { forceToRefreshQuery } from 'shared/queryClient';
import { updateServiceInstanceNum } from '../shared';
import { modelDirectionTypeToTextMap, getDotState, getTableFilterValue } from '../shared';
import { CONSTANTS } from 'shared/constants';

import { Spin, Button, Message, Grid, Tooltip } from '@arco-design/web-react';
import SharedPageLayout from 'components/SharedPageLayout';
import StateIndicator from 'components/StateIndicator';
import BackButton from 'components/BackButton';
import MoreActions from 'components/MoreActions';
import PropertyList from 'components/PropertyList';
import GridRow from 'components/_base/GridRow';
import Modal from 'components/Modal';
import UserGuideTab from '../UserGuideTab';
import InstanceTable from '../InstanceTable';
import WhichModel from 'components/WhichModel';

import {
  ModelServing,
  ModelDirectionType,
  ModelServingInstance,
  ModelServingState,
} from 'typings/modelServing';
import { SortDirection, SorterResult } from '@arco-design/web-react/es/Table/interface';

import styles from './index.module.less';

type Props = {};

const ModelServingDetail: FC<Props> = () => {
  const { id } = useParams<{
    id: string;
    tabType: string;
  }>();

  const history = useHistory();
  const [urlState, setUrlState] = useUrlState<Record<string, string | undefined>>({
    order_by: undefined,
    instances_status: undefined,
  });

  const projectId = useGetCurrentProjectId();

  const modelServingDetailQuery = useQuery(
    ['fetchModelServingDetail', id, urlState.order_by],

    () => {
      if (!projectId) {
        Message.info('请选择工作区');
        return;
      }
      return fetchModelServingDetail_new(projectId!, id, {
        order_by: urlState.order_by || 'created_at desc',
      });
    },
    {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const modelServingDetail = useMemo<ModelServing>(() => {
    const emptyData = {} as ModelServing;

    if (!modelServingDetailQuery.data || !modelServingDetailQuery.data.data) {
      return emptyData;
    }
    return modelServingDetailQuery.data.data;
  }, [modelServingDetailQuery.data]);

  const displayedProps = useMemo(() => {
    const modelDirectionText =
      modelDirectionTypeToTextMap[
        modelServingDetail.is_local ? ModelDirectionType.HORIZONTAL : ModelDirectionType.VERTICAL
      ];

    const { instance_num_status: instanceAmount } = modelServingDetail;
    let payload;
    try {
      payload = JSON.parse(
        modelServingDetail.remote_platform?.payload || JSON.stringify({ target_psm: '-' }),
      );
    } catch (error) {}
    const thirdServingDisplayedList = [
      {
        value:
          <StateIndicator {...getDotState(modelServingDetail)} /> || CONSTANTS.EMPTY_PLACEHOLDER,
        label: '状态',
      },
      {
        value: modelDirectionText || CONSTANTS.EMPTY_PLACEHOLDER,
        label: '模型类型',
      },
      {
        value: (
          <WhichModel
            id={modelServingDetail.model_id}
            isModelGroup={Boolean(modelServingDetail.model_group_id)}
          />
        ),
        label: '模型',
      },
      {
        value:
          instanceAmount !== 'UNKNOWN'
            ? instanceAmount || CONSTANTS.EMPTY_PLACEHOLDER
            : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '实例数量',
      },
      {
        value:
          (
            <a href={modelServingDetail.endpoint} target="_blank" rel="noreferrer">
              {payload?.target_psm}
            </a>
          ) || CONSTANTS.EMPTY_PLACEHOLDER,
        label: 'psm',
      },

      {
        value: modelServingDetail.created_at
          ? formatTimestamp(modelServingDetail.created_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '创建时间',
      },
      {
        value: modelServingDetail.updated_at
          ? formatTimestamp(modelServingDetail.updated_at)
          : CONSTANTS.EMPTY_PLACEHOLDER,
        label: '更新时间',
      },
    ];
    const innerServingDisplayedList = cloneDeep(thirdServingDisplayedList);
    innerServingDisplayedList.splice(4, 1);
    return modelServingDetail?.remote_platform
      ? thirdServingDisplayedList
      : innerServingDisplayedList;
  }, [modelServingDetail]);

  const sorterProps = useMemo<Record<string, SortDirection>>(() => {
    if (urlState.order_by) {
      const order = urlState.order_by?.split(' ') || [];
      return {
        [order[0]]: order?.[1] === 'asc' ? 'ascend' : 'descend',
      };
    }

    return {};
  }, [urlState.order_by]);

  const isLoading = modelServingDetailQuery.isFetching;
  const tableDataList = modelServingDetail?.instances ?? [];

  return (
    <SharedPageLayout
      title={<BackButton onClick={goBack}>{'在线服务'}</BackButton>}
      cardPadding={0}
      isNestSpinFlexContainer={true}
    >
      <Spin loading={isLoading}>
        <div className={styles.padding_container}>
          <Grid.Row align="center" justify="space-between">
            <GridRow gap="12" style={{ maxWidth: '75%' }}>
              <div
                className={styles.avatar_container}
                data-name={
                  modelServingDetail.name
                    ? modelServingDetail.name.slice(0, 1)
                    : CONSTANTS.EMPTY_PLACEHOLDER
                }
              />
              <div>
                <h3 className={styles.name}>{modelServingDetail.name ?? '...'}</h3>
                <Tooltip content={modelServingDetail?.comment}>
                  <small className={styles.comment}>
                    {modelServingDetail?.comment || CONSTANTS.EMPTY_PLACEHOLDER}
                  </small>
                </Tooltip>
              </div>
            </GridRow>

            <GridRow>
              <Button
                className={styles.change_button}
                type="primary"
                disabled={
                  modelServingDetail.status !== ModelServingState.AVAILABLE ||
                  modelServingDetail.resource === undefined
                }
                onClick={onScaleClick}
              >
                扩缩容
              </Button>
              <MoreActions
                actionList={[
                  {
                    label: '编辑',
                    onClick: onChangeClick,
                  },
                  {
                    label: '删除',
                    onClick: onDeleteClick,
                    danger: true,
                  },
                ]}
              />
            </GridRow>
          </Grid.Row>
          <PropertyList cols={4} colProportions={[1, 1, 2, 1]} properties={displayedProps} />

          <p className={styles.title}>调用指南</p>
          {!modelServingDetail.is_local &&
          !modelServingDetail.support_inference &&
          !modelServingDetail.remote_platform ? (
            <div className={styles.inference_hidden_info}>
              纵向模型服务仅发起方可查看调用地址和 Signature
            </div>
          ) : (
            <UserGuideTab
              isShowLabel={false}
              isShowSignature={!modelServingDetail.remote_platform}
              data={modelServingDetail}
            />
          )}
          {modelServingDetail.resource !== undefined && (
            <>
              <p className={styles.title}>实例列表</p>
              <InstanceTable
                sorter={sorterProps}
                filter={{
                  instances_status: getTableFilterValue(urlState.instances_status),
                }}
                total={tableDataList.length}
                dataSource={tableDataList}
                loading={modelServingDetailQuery.isFetching}
                onLogClick={onLogClick}
                onChange={onTableChange}
              />
            </>
          )}
        </div>
      </Spin>
    </SharedPageLayout>
  );

  function goBack() {
    history.goBack();
  }

  function onLogClick(record: ModelServingInstance) {
    window.open(`/v2/logs/model-serving/${id}/${record.name}`, '_blank noopener');
  }

  async function onChangeClick() {
    if (modelServingDetail.id) {
      history.push(`/model-serving/edit/${modelServingDetail.id}`);
    }
  }

  async function onScaleClick() {
    updateServiceInstanceNum(modelServingDetail, () => {
      forceToRefreshQuery(['fetchModelServingDetail', id]);
    });
  }

  function onDeleteClick() {
    if (!projectId) {
      Message.info('请选择工作区！');
      return;
    }
    Modal.delete({
      title: `确认要删除「${modelServingDetail.name}」？`,
      content: '一旦删除，在线服务相关数据将无法复原，请谨慎操作',
      onOk() {
        deleteModelServing_new(projectId!, modelServingDetail.id)
          .then(() => {
            Message.success('删除成功');
            history.replace('/model-serving');
          })
          .catch((error) => {
            Message.error(error.message);
          });
      },
    });
  }

  function onTableChange(
    _: any,
    sorter: SorterResult | SorterResult[],
    filters: Record<string, any>,
    extra: { action: string },
  ) {
    const { action } = extra;
    const latestSorter = Array.isArray(sorter) ? sorter[0] : sorter;

    if (action === 'sort' && latestSorter.field && latestSorter.direction) {
      setUrlState({
        order_by: `${latestSorter.field as string} ${
          latestSorter.direction === 'ascend' ? 'asc' : 'desc'
        }`,
      });
    } else {
      setUrlState({
        order_by: undefined,
      });
    }

    if (action === 'filter') {
      setUrlState({
        instances_status: filters.status?.[0] || undefined,
      });
    }
  }
};

export default ModelServingDetail;
