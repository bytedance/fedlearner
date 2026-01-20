import React, { FC, useMemo } from 'react';
import ConfigForm, { ItemProps } from 'components/ConfigForm';
import { to, isStringCanBeParsed } from 'shared/helpers';
import { fetchDataJobVariableDetail, analyzeDataBatch } from 'services/dataset';
import { Modal, Button, Message, Form } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import ButtonWithPopconfirm from 'components/ButtonWithPopconfirm';
import { useQuery } from 'react-query';
import { DataBatchV2, DataJobBackEndType, DataJobVariable } from 'typings/dataset';
import { useParams } from 'react-router';
import {
  Variable,
  VariableComponent,
  VariableValueType,
  VariableWidgetSchema,
} from 'typings/variable';
import { TAG_MAPPER, VARIABLE_TIPS_MAPPER, NO_CATEGORY } from '../../../shared';
import { Tag as TagEnum } from 'typings/workflow';
import { hydrate } from 'views/Workflows/shared';
import styled from './index.module.less';

type Props = {
  dataBatch: DataBatchV2;
  visible: boolean;
  toggleVisible: (v: boolean) => void;
  onSuccess?: (res: any) => void;
} & React.ComponentProps<typeof Modal>;
type Params = {
  [key: string]: any;
};
type FormData = {
  params: Params;
};

const DataBatchAnalyzeModal: FC<Props> = ({
  dataBatch,
  visible,
  toggleVisible,
  onSuccess,
  ...props
}) => {
  const [form] = Form.useForm<FormData>();
  const { id: dataBatchId } = dataBatch;
  const { id } = useParams<{
    id: string;
  }>();
  const dataJobVariableDetailQuery = useQuery(
    ['getDataJobVariableDetail', DataJobBackEndType.ANALYZER],
    () => fetchDataJobVariableDetail(DataJobBackEndType.ANALYZER),
    {
      enabled: true,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  );

  const dataJobVariableList = useMemo<Variable[]>(() => {
    if (!dataJobVariableDetailQuery.data?.data?.variables) {
      return [];
    }

    return dataJobVariableDetailQuery.data.data.variables.map((item) => {
      let widget_schema: VariableWidgetSchema = {};

      try {
        widget_schema = JSON.parse(item.widget_schema);
      } catch (error) {}

      return {
        ...item,
        widget_schema,
      };
    });
  }, [dataJobVariableDetailQuery.data]);

  const paramsList = useMemo<ItemProps[]>(() => {
    const list: ItemProps[] = [];
    dataJobVariableList
      .filter((item) => !item.widget_schema.hidden)
      .forEach((item) => {
        const baseRuleList = item.widget_schema.required
          ? [
              {
                required: true,
                message: '必填项',
              },
            ]
          : [];

        list.push({
          tip: VARIABLE_TIPS_MAPPER[item.name],
          label: item.name,
          tag: TAG_MAPPER[item.tag as TagEnum] || NO_CATEGORY,
          field: item.name,
          initialValue:
            item.widget_schema.component === VariableComponent.Input
              ? item.value
              : item.typed_value,
          componentType: item.widget_schema.component,
          rules:
            item.widget_schema.component === VariableComponent.Input &&
            [VariableValueType.LIST, VariableValueType.OBJECT].includes(item.value_type!)
              ? [
                  ...baseRuleList,
                  {
                    validator: (value, callback) => {
                      if ((value && typeof value === 'object') || isStringCanBeParsed(value)) {
                        callback();
                        return;
                      }
                      callback(`JSON ${item.value_type} 格式错误`);
                    },
                  },
                ]
              : baseRuleList,
        });
      });
    return list;
  }, [dataJobVariableList]);
  return (
    <Modal
      title="发起数据探查"
      visible={visible}
      maskClosable={false}
      maskStyle={{ backdropFilter: 'blur(4px)' }}
      afterClose={afterClose}
      onCancel={closeModal}
      okText="探查"
      footer={null}
      {...props}
    >
      <Form layout="vertical" form={form} onSubmit={submit}>
        <Form.Item label="参数配置" field="params">
          <ConfigForm
            filter={variableTagFilter}
            groupBy={'tag'}
            hiddenGroupTag={true}
            hiddenCollapse={true}
            cols={2}
            formItemList={paramsList}
            isResetOnFormItemListChange={true}
          />
        </Form.Item>

        <Form.Item wrapperCol={{ span: 24 }} style={{ marginBottom: 0 }}>
          <GridRow className={styled.footer_row} justify="end" gap="12">
            <ButtonWithPopconfirm buttonText="取消" onConfirm={closeModal} />
            <Button type="primary" htmlType="submit">
              探查
            </Button>
          </GridRow>
        </Form.Item>
      </Form>
    </Modal>
  );

  function variableTagFilter(item: ItemProps) {
    return (
      !!item.tag &&
      [TAG_MAPPER[TagEnum.INPUT_PARAM], TAG_MAPPER[TagEnum.RESOURCE_ALLOCATION]].includes(item.tag)
    );
  }

  function closeModal() {
    toggleVisible(false);
  }

  async function submit(values: { params: Params }) {
    if (!form) {
      return;
    }
    const { params } = values;
    const [res, error] = await to(
      analyzeDataBatch(id, dataBatchId, {
        dataset_job_config: {
          variables: hydrate(dataJobVariableList, params, {
            isStringifyVariableValue: true,
            isStringifyVariableWidgetSchema: true,
            isProcessVariableTypedValue: true,
          }) as DataJobVariable[],
        },
      }),
    );
    if (error) {
      Message.error(error.message);
      return;
    }
    Message.success('数据探查发起成功');
    closeModal();
    onSuccess?.(res);
  }

  function afterClose() {
    form.resetFields();
  }
};

export default DataBatchAnalyzeModal;
