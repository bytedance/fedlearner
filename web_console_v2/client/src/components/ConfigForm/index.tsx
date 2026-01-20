/* istanbul ignore file */
import React, {
  useEffect,
  useMemo,
  useImperativeHandle,
  ForwardRefRenderFunction,
  forwardRef,
  ReactNode,
} from 'react';
import i18n from 'i18n';

import { Grid, Form, Input, Collapse, InputNumber, Select, Switch } from '@arco-design/web-react';
import { IconQuestionCircle } from '@arco-design/web-react/icon';
import ModelCodesEditorButton from 'components/ModelCodesEditorButton';
import YAMLTemplateEditorButton from 'components/YAMLTemplateEditorButton';
import EnvsInputForm from 'views/WorkflowTemplates/TemplateConfig/JobComposeDrawer/VariableList/VariableItem/EnvsInputForm';
import { AlgorithmSelect } from 'components/DoubleSelect';
import { CpuInput, MemInput } from 'components/InputGroup/NumberTextInput';
import TitleWithIcon from 'components/TitleWithIcon';

import { FormProps, FormItemProps, FormInstance } from '@arco-design/web-react/es/Form';
import { VariableComponent } from 'typings/variable';
import { NO_CATEGORY } from 'views/Datasets/shared';
import './index.less';

const { Row, Col } = Grid;

export type ItemProps = {
  componentType?: `${VariableComponent}`;
  componentProps?: object;
  tip?: string;
  render?: (props: object) => React.ReactNode;
  tag?: string;
} & FormItemProps;

export type ExposedRef = {
  formInstance: FormInstance;
};

type Props = {
  value?: { [key: string]: any };
  onChange?: (val: any) => void;
  /** Extra form props */
  formProps?: FormProps;
  /** Extra for action*/
  configFormExtra?: ReactNode;
  /** Form item list */
  formItemList?: ItemProps[];
  /** Collapse form item list */
  collapseFormItemList?: ItemProps[];
  /** Collapse title */
  collapseTitle?: string;
  /** Collapse title extra node */
  collapseTitleExtra?: ReactNode;
  /** Is default open collapse */
  isDefaultOpenCollapse?: boolean;
  /** How many cols in one row */
  cols?: 1 | 2 | 3 | 4 | 6 | 8 | 12 | 24;
  /** Reset initialValues when changing formItemList or collapseFormItemList */
  isResetOnFormItemListChange?: boolean;
  /** variable will be grouped by this field */
  groupBy?: string;
  /** Is group tag Hidden */
  hiddenGroupTag?: boolean;
  /** Is Collapse Hidden*/
  hiddenCollapse?: boolean;
  /** filter */
  filter?: (item: ItemProps) => boolean;
};

const emptyList: ItemProps[] = [];
interface ItemMapper {
  [tagKey: string]: {
    list: ItemProps[];
    rows: number;
  };
}

const ConfigForm: ForwardRefRenderFunction<ExposedRef, Props> = (
  {
    value,
    onChange,
    formProps,
    configFormExtra,
    formItemList = emptyList,
    collapseFormItemList = emptyList,
    collapseTitle = i18n.t('model_center.title_advanced_config'),
    collapseTitleExtra,
    isDefaultOpenCollapse = false,
    isResetOnFormItemListChange = false,
    cols = 2,
    groupBy = '',
    hiddenGroupTag = true,
    hiddenCollapse = false,
    filter,
  },
  parentRef,
) => {
  const isControlled = typeof value === 'object' && value !== null;
  const [form] = Form.useForm();

  const initialFormValue = useMemo(() => {
    const list = [...formItemList, ...collapseFormItemList];

    return list.reduce((acc, cur) => {
      const { field, initialValue } = cur;

      if (field) {
        acc[field] = initialValue;
      }

      return acc;
    }, {} as any);
  }, [formItemList, collapseFormItemList]);

  const span = useMemo(() => {
    return Math.floor(24 / cols);
  }, [cols]);

  const getGroupedItemMapper = (
    itemList: ItemProps[],
    groupBy: string,
    cols: number,
    filter?: (item: ItemProps) => boolean,
  ) => {
    return itemList?.reduce((acc: ItemMapper, cur: any) => {
      // Executive filter
      if (filter && !filter(cur)) {
        return acc;
      }
      const tag = cur[groupBy] || NO_CATEGORY;
      if (!acc[tag]) {
        acc[tag] = {
          list: [],
          rows: 0,
        };
      }
      acc[tag]?.list?.push({ ...cur });
      acc[tag].rows = Math.ceil(acc[tag]?.list?.length / cols);
      return acc;
    }, {} as ItemMapper);
  };

  const groupedFormItemMapper = useMemo(() => {
    return getGroupedItemMapper(formItemList, groupBy, cols, filter);
  }, [formItemList, groupBy, cols, filter]);
  const groupedCollapseFormItemMapper = useMemo(() => {
    return getGroupedItemMapper(collapseFormItemList, groupBy, cols, filter);
  }, [collapseFormItemList, groupBy, cols, filter]);

  useEffect(() => {
    if (isControlled) {
      form.setFieldsValue({ ...value });
    }
  }, [value, isControlled, form]);

  useEffect(() => {
    if (isResetOnFormItemListChange) {
      onChange?.(initialFormValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialFormValue, isResetOnFormItemListChange]);

  useImperativeHandle(parentRef, () => {
    return {
      formInstance: form,
    };
  });

  const renderFormItemList = (
    groupedFormItemMapper: ItemMapper,
    cols: number,
    span: number,
    hiddenGroupTag: boolean,
  ) => {
    return Object.keys(groupedFormItemMapper).reduce((acc: any, cur: string) => {
      const { list = [] as ItemProps[], rows } = groupedFormItemMapper[cur];
      !hiddenGroupTag &&
        !!groupBy &&
        acc.push(
          <Row gutter={16} key={cur}>
            <span className="config-form-variable-label">{cur}</span>
          </Row>,
        );
      for (let i = 0; i < rows; i++) {
        acc.push(
          <Row gutter={16} key={'' + cur + i}>
            {list.slice(i * cols, (i + 1) * cols).map((item: ItemProps, index: number) => {
              const { componentType, componentProps, render, label, tip, ...restProps } = item;
              return (
                <Col span={span} key={index}>
                  <Form.Item
                    {...restProps}
                    layout="vertical"
                    label={
                      tip && typeof label === 'string' ? (
                        <TitleWithIcon
                          isBlock={false}
                          icon={IconQuestionCircle}
                          isShowIcon={true}
                          title={label}
                          tip={tip}
                        />
                      ) : (
                        label
                      )
                    }
                  >
                    {renderFormItemContent(item)}
                  </Form.Item>
                </Col>
              );
            })}
          </Row>,
        );
      }
      return acc;
    }, [] as any);
  };

  return (
    <Form
      className="config-form"
      form={form}
      initialValues={initialFormValue}
      onChange={(val: any, values: any) => {
        onChange?.(values);
      }}
      scrollToFirstError
      {...formProps}
    >
      <div className="config-form-extra">{configFormExtra}</div>
      {renderFormItemList(groupedFormItemMapper, cols, span, hiddenGroupTag)}
      {!hiddenCollapse && (
        <Collapse
          className="config-form-collapse"
          defaultActiveKey={isDefaultOpenCollapse ? ['1'] : []}
          expandIconPosition="left"
          lazyload={false}
          bordered={false}
        >
          <Collapse.Item header={collapseTitle} name="1" extra={collapseTitleExtra}>
            {renderFormItemList(groupedCollapseFormItemMapper, cols, span, hiddenGroupTag)}
          </Collapse.Item>
        </Collapse>
      )}
    </Form>
  );
};

function renderFormItemContent(props: ItemProps) {
  const { componentType, componentProps = {}, render } = props;

  if (render) {
    return render(componentProps);
  }

  const Component = getRenderComponent(componentType) || Input;

  return <Component {...componentProps} />;
}

export function getRenderComponent(componentType?: VariableComponent | `${VariableComponent}`) {
  let Component: React.Component<any> | React.FC<any> = Input;
  switch (componentType) {
    case VariableComponent.Input:
      Component = Input;
      break;
    case VariableComponent.TextArea:
      Component = Input.TextArea;
      break;
    case VariableComponent.NumberPicker:
      Component = InputNumber;
      break;
    case VariableComponent.Select:
      Component = Select;
      break;
    case VariableComponent.Switch:
      Component = Switch;
      break;
    case VariableComponent.Code:
      Component = ModelCodesEditorButton;
      break;
    case VariableComponent.JSON:
      Component = YAMLTemplateEditorButton;
      break;
    case VariableComponent.EnvsInput:
      Component = EnvsInputForm;
      break;
    case VariableComponent.AlgorithmSelect:
      Component = AlgorithmSelect;
      break;
    case VariableComponent.CPU:
      Component = CpuInput;
      break;
    case VariableComponent.MEM:
      Component = MemInput;
      break;
    default:
      Component = Input;
      break;
  }
  return Component;
}

export default forwardRef(ConfigForm);
