/* istanbul ignore file */

import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { giveWeakRandomKey, transformRegexSpecChar } from 'shared/helpers';

import { Select, Button, Input, Message, SelectProps } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { Check, Close } from 'components/IconPark';

export interface OptionItem {
  label: string;
  value: any;
  isCreating?: boolean;
  id?: string;
}

export interface Props extends SelectProps {
  value?: any[];
  onChange?: (val: any) => void;
  onInputConfirm?: (val: any) => void;
  optionList: OptionItem[];
  addTypeText?: string;
  typeInputPlaceholader?: string;
}

const Footer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  padding-top: 4px;
  border-top: 1px solid var(--lineColor);
`;

const LabelStrong = styled.span`
  font-size: 14px;
  color: var(--textColorStrong);
  white-space: normal;
  word-break: break-all;
`;
const LabelIndex = styled.span`
  display: inline-block;
  width: 30px;
  font-size: 14px;
  color: var(--textColorSecondary);
`;

const ItemCotainer = styled.div`
  display: flex;
  width: 100%;
  justify-content: space-between;
`;

const Left = styled.div`
  display: flex;
  flex: 1;
  align-items: center;
`;
const ButtonGroup = styled.div`
  flex: 0 0 60px;
  display: flex;
  justify-content: space-around;
  align-items: center;
`;

const StyledInput = styled(Input)`
  flex: 1;
  background-color: transparent;
  &:hover {
    background-color: #fff;
    border: 1px solid #2761f6;
  }
`;

const AddTypeSelect: FC<Props> = ({
  value,
  onChange = () => {},
  onInputConfirm = () => {},
  optionList,
  addTypeText = '新增类型',
  typeInputPlaceholader = '请输入算法类型',
  ...props
}) => {
  const [tempList, setTempList] = useState<OptionItem[]>([]);

  return (
    <Select
      value={value}
      showSearch={true}
      filterOption={(inputValue, option) => {
        if (option && option.props.extra) {
          const regx = new RegExp(`^.*${transformRegexSpecChar(inputValue)}.*$`);
          return regx.test(option.props.extra as string);
        }

        return false;
      }}
      onChange={(value, options) => {
        onChange(value);
      }}
      dropdownRender={(menu) => (
        <div>
          {menu}
          <Footer>
            <Button type="text" icon={<IconPlus />} onClick={onCreateClick}>
              {addTypeText}
            </Button>
          </Footer>
        </div>
      )}
      {...props}
    >
      {optionList.concat(tempList).map((item, index) => {
        return (
          <Select.Option key={item.id || item.value} value={item.value} extra={item.label}>
            <ItemCotainer
              onClick={(e: any) => {
                if (item.isCreating) {
                  e.stopPropagation();
                }
              }}
            >
              <Left>
                <LabelIndex>{index + 1}</LabelIndex>
                {item.isCreating ? (
                  <StyledInput
                    autoFocus
                    defaultValue={item.value}
                    placeholder={typeInputPlaceholader}
                    onClick={(e: any) => {
                      e.stopPropagation();
                      e.target.focus();
                    }}
                    onChange={(inputValue) => {
                      setTempList((prevState) =>
                        prevState.map((innerItem) => {
                          if (item.id === innerItem.id) {
                            return { ...innerItem, value: inputValue, label: inputValue };
                          }
                          return innerItem;
                        }),
                      );
                    }}
                    onPressEnter={(e: any) => {
                      const inputValue = e.target.value;
                      if (!inputValue) {
                        Message.error({
                          content: typeInputPlaceholader,
                        });
                        e.stopPropagation();
                        return;
                      }
                      setTempList((prevState) =>
                        prevState.map((innerItem) => {
                          if (item.id === innerItem.id) {
                            return {
                              ...innerItem,
                              isCreating: false,
                              value: inputValue,
                              label: inputValue,
                            };
                          }
                          return innerItem;
                        }),
                      );
                      onInputConfirm(inputValue);
                    }}
                  />
                ) : (
                  <LabelStrong>{item.label}</LabelStrong>
                )}
              </Left>
              {item.isCreating && (
                <ButtonGroup>
                  <Check
                    onClick={(e) => {
                      e.stopPropagation();

                      if (!item.value) {
                        Message.error({
                          content: typeInputPlaceholader,
                        });
                        return;
                      }

                      setTempList((prevState) =>
                        prevState.map((innerItem) => {
                          if (item.id === innerItem.id) {
                            return { ...innerItem, isCreating: false };
                          }
                          return { ...innerItem };
                        }),
                      );
                      onInputConfirm(item.value);
                    }}
                  />
                  <Close
                    onClick={(e) => {
                      e.stopPropagation();
                      setTempList((prevState) =>
                        prevState.filter((innerItem) => item.id !== innerItem.id),
                      );
                    }}
                  />
                </ButtonGroup>
              )}
            </ItemCotainer>
          </Select.Option>
        );
      })}
    </Select>
  );

  function onCreateClick() {
    setTempList((prevState) =>
      prevState.concat([
        {
          label: '',
          value: '',
          isCreating: true,
          id: giveWeakRandomKey(),
        },
      ]),
    );
  }
};

export default AddTypeSelect;
