import React, { CSSProperties, FC, useEffect, useMemo } from 'react';
import {
  InputNumberProps,
  Grid,
  Form,
  Input,
  InputNumber,
  Button,
  RulesProps,
  Tooltip,
  Space,
} from '@arco-design/web-react';
import { IconDelete, IconPlus, IconQuestionCircle } from '@arco-design/web-react/icon';
import styled from 'styled-components';
import NumberTextInput from './NumberTextInput';

export type TColumn = TInputColumn | TInputNumberColumn | TTextColumn;

interface TInputColumn extends TColumnBasic {
  type: 'INPUT';
  formatValue?: (value: string, column: TColumn, allValues: TValue[]) => string;
}
interface TInputNumberColumn
  extends Pick<InputNumberProps, 'min' | 'max' | 'precision' | 'mode'>,
    TColumnBasic {
  type: 'INPUT_NUMBER';
  formatValue?: (value: number, column: TColumn, allValues: TValue[]) => number;
}
interface TTextColumn extends TColumnBasic {
  type: 'TEXT';
  unitLabel?: string;
}

interface TColumnBasic {
  title: string;
  dataIndex: string;
  span: number;
  placeholder?: string;
  unitLabel?: string;
  rules?: RulesProps[];
  tooltip?: string;
  disabled?: boolean;
}

type TValue = Record<string, any>;
type TInnerValue = { [key: string]: TValue[] };
type TProps = {
  /** customize style */
  style?: CSSProperties;
  /** addition className */
  className?: string;
  /** Definition of grid column */
  columns: TColumn[];
  /** Default value of form grid, often is an array of object */
  defaultValue?: TValue[];
  /** Use value to control the component when under controlled mode */
  value?: TValue[];
  /**
   * @description Customize text on the button of "add a new row"
   * @default "add"
   */
  /** text of add button  */
  addBtnText?: string;
  /** disable add and delete */
  disableAddAndDelete?: boolean;
  /** listen for the values changing */
  onChange?: (data: TValue[]) => void;
};

export type TInputGroupProps = TProps;

const StyledContainer = styled.div`
  .arco-input {
    font-size: var(--textFontSizePrimary);
  }
  .arco-form-item {
    margin-bottom: 8px;
  }
`;
const StyledPlainText = styled.span`
  display: flex;
  box-sizing: border-box;
  min-width: 111px;
  height: 32px;
  border-radius: 2px;
  border: 1px solid #e5e8ef;
  padding: 0 12px;
  line-height: 32px;
  .plainSuffix {
    flex: 1;
    text-align: right;
  }
`;
const StyledHeader = styled.header`
  margin-bottom: 6px;
`;
const StyledTitle = styled.span`
  line-height: 20px;
  font-size: var(--textFontSizePrimary);
  color: var(--textColor);
`;
const StyledDeleteBtn = styled(Button)`
  margin-top: 2px;
  color: var(--textColor) !important;
`;
const StyledAddButton = styled(Button)`
  width: 100px;
  margin-left: -5px;
  padding-left: 5px;
  padding-right: 5px;
  text-align: left;
  font-size: var(--textFontSizePrimary);
  &.arco-btn-text:not(.arco-btn-disabled):not(.arco-btn-loading):hover {
    background: transparent;
  }
`;
const StyledQuestionIcon = styled(IconQuestionCircle)`
  font-size: var(--textFontSizePrimary);
  color: var(--textColor);
`;

const { Row, Col } = Grid;
const ROOT_FIELD = 'root';
const FORM_FIELD_SPAN = 22;
const ROW_GUTTER = 12;
const InputGroup: FC<TProps> = (props) => {
  const [form] = Form.useForm();
  const {
    value,
    style,
    className,
    columns,
    addBtnText = 'add',
    defaultValue = [],
    disableAddAndDelete = false,
    onChange,
  } = props;
  const controlled = Object.prototype.hasOwnProperty.call(props, 'value');

  const columnSpanList = useMemo(() => {
    let noSpanCount = columns.length;
    let occupiedSpan = 0;

    for (const col of columns) {
      if (col.span) {
        noSpanCount -= 1;
        occupiedSpan += col.span;
      }
    }

    if (noSpanCount > 0) {
      throw new Error('InputGroup: every column should have span');
    }

    if (occupiedSpan !== 24) {
      throw new Error('InputGroup: total columns span must be equal to 24');
    }

    return columns.map((col) => col.span);
  }, [columns]);
  useEffect(() => {
    if (controlled) {
      form.setFieldValue(ROOT_FIELD, value);
    }
  }, [value, controlled, form]);

  return (
    <StyledContainer style={style} className={className}>
      <StyledHeader>
        <Row gutter={ROW_GUTTER}>
          <Col span={!disableAddAndDelete ? FORM_FIELD_SPAN : 24}>
            <Row gutter={ROW_GUTTER}>
              {columns.map((column, i) => (
                <Col span={columnSpanList[i]} key={column.dataIndex}>
                  <Space>
                    <StyledTitle>{column.title}</StyledTitle>
                    {column.tooltip && (
                      <Tooltip content={column.tooltip}>
                        <StyledQuestionIcon data-testid="tooltip-icon" />
                      </Tooltip>
                    )}
                  </Space>
                </Col>
              ))}
            </Row>
          </Col>
        </Row>
      </StyledHeader>
      <div>
        <Form
          form={form}
          initialValues={{
            [ROOT_FIELD]: value || defaultValue || [],
          }}
          onChange={(_, allValue: TInnerValue) => {
            form.validate((error) => {
              if (!error) {
                onChangeWrapper(allValue[ROOT_FIELD]);
              }
            });
          }}
        >
          <Form.List field={ROOT_FIELD}>
            {(fields, { remove, add }) => {
              return (
                <>
                  {fields.map((item, index) => {
                    return (
                      <Row gutter={ROW_GUTTER} key={item.field + item.key}>
                        <Col span={!disableAddAndDelete ? FORM_FIELD_SPAN : 24}>
                          <Row gutter={ROW_GUTTER}>
                            {columns.map((col, i) => {
                              const { dataIndex, rules } = col;
                              const field = item.field + '.' + dataIndex;
                              return (
                                <Col key={field} span={columnSpanList[i]}>
                                  <Form.Item
                                    role="gridcell"
                                    rules={rules}
                                    field={field}
                                    wrapperCol={{ span: 24 }}
                                  >
                                    {renderFormItem(col)}
                                  </Form.Item>
                                </Col>
                              );
                            })}
                          </Row>
                        </Col>
                        {!disableAddAndDelete && (
                          <Col span={24 - FORM_FIELD_SPAN}>
                            <StyledDeleteBtn
                              name="delete row button"
                              size="small"
                              type="text"
                              data-index={index}
                              data-testid="delBtn"
                              icon={<IconDelete />}
                              onClick={() => {
                                controlled
                                  ? performFormActionUnderControlled('delete', index)
                                  : remove(index);
                              }}
                            />
                          </Col>
                        )}
                      </Row>
                    );
                  })}
                  {!disableAddAndDelete && (
                    <StyledAddButton
                      type="text"
                      data-testid="addBtn"
                      icon={<IconPlus />}
                      onClick={() => {
                        controlled
                          ? performFormActionUnderControlled('add')
                          : add(getDefaultRowValueFromColumns(columns));
                      }}
                    >
                      {addBtnText}
                    </StyledAddButton>
                  )}
                </>
              );
            }}
          </Form.List>
        </Form>
      </div>
    </StyledContainer>
  );

  function onChangeWrapper(values: TValue[]) {
    const formattedValues = values.map((row) => {
      for (const k in row) {
        const col = columns.find((col) => col.dataIndex === k);
        if (!col) {
          continue;
        }
        if (
          (col.type === 'INPUT' || col.type === 'INPUT_NUMBER') &&
          typeof col.formatValue === 'function'
        ) {
          row[k] = col.formatValue(row[k] as never, col, values);
        }
      }
      return row;
    });

    onChange?.(formattedValues);
  }

  function performFormActionUnderControlled(action: 'add' | 'delete', index?: number) {
    const currentValues = [...(form.getFieldValue(ROOT_FIELD) ?? [])];

    if (action === 'add') {
      currentValues.push(getDefaultRowValueFromColumns(columns));
    } else {
      currentValues.splice(index!, 1);
    }
    onChangeWrapper(currentValues);
  }
};

function getDefaultRowValueFromColumns(columns: TColumn[]) {
  const ret: Record<string, any> = {};
  for (const col of columns) {
    switch (col.type) {
      case 'INPUT':
      case 'TEXT':
        ret[col.dataIndex] = '';
        break;
      case 'INPUT_NUMBER':
        ret[col.dataIndex] = col.min ?? 0;
        break;
    }
  }

  return ret;
}

function renderFormItem(column: TColumn) {
  switch (column.type) {
    case 'INPUT':
      return (
        <Input
          placeholder={column.placeholder}
          suffix={column.unitLabel}
          disabled={column.disabled}
        />
      );
    case 'INPUT_NUMBER':
      return column.mode ? (
        <InputNumber
          min={column.min}
          max={column.max}
          precision={column.precision}
          mode={column.mode}
          suffix={column.unitLabel}
          disabled={column.disabled}
        />
      ) : (
        <NumberTextInput
          min={column.min}
          max={column.max}
          precision={column.precision}
          mode={column.mode}
          suffix={column.unitLabel}
          disabled={column.disabled}
        />
      );
    case 'TEXT':
      return <PlainText suffix={column.unitLabel} />;
  }
}

type TPlainTextProps = {
  suffix?: string;
  value?: string | number;
  defaultValue?: string | number;
};
function PlainText({ suffix, defaultValue, value }: TPlainTextProps) {
  const purifyValue = useMemo(() => {
    if (!value) {
      return '';
    }

    if (!suffix) {
      return value;
    }

    if (typeof value === 'string') {
      // there may be an unit label at tail
      const tailString = value.slice(-1 * suffix.length);
      if (tailString === suffix) {
        return value.slice(0, value.length - suffix.length);
      }
    }

    return value;
  }, [suffix, value]);
  return (
    <StyledPlainText>
      {purifyValue || defaultValue || ''}
      {suffix ? <span className="plainSuffix">{suffix}</span> : null}
    </StyledPlainText>
  );
}

export default InputGroup;
