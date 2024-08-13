import { Button, Input, Form } from '@arco-design/web-react';
import { Plus } from 'components/IconPark';
import NoResult from 'components/NoResult';
import React, { FC, memo, useCallback, useContext, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import styled from './index.module.less';
import { giveDefaultVariable } from 'views/WorkflowTemplates/TemplateForm/stores';
import { SearchBox } from '../elements';
import { useSearchBox } from '../hooks';
import { ComposeDrawerContext } from '../index';
import VariableItem from './VariableItem';

const VariableList: FC<{ isCheck?: boolean }> = ({ isCheck }) => {
  const { t } = useTranslation();
  const { filter, onFilterChange, onInputKeyPress } = useSearchBox();

  const context = useContext(ComposeDrawerContext);
  const varRemoverRerf = useRef<((index: number) => void) | undefined>(undefined);
  const varNameFilter = useCallback(
    (_: any, index: number) => {
      const matcher = filter.toLowerCase();
      const variable = context.formData?.variables![index];

      return variable?.name?.toLowerCase().includes(matcher);
    },
    [filter, context],
  );

  return (
    <>
      <SearchBox>
        <Input.Search
          placeholder="按名字搜索变量"
          onChange={onFilterChange}
          onKeyPress={onInputKeyPress}
        />
      </SearchBox>

      <Form.List field="variables">
        {(fields, { add, remove }) => {
          const filteredItems = fields.filter(varNameFilter as any);
          /**
           * Due to every time rerender variable list, the remove method
           * will change ref, and it lead VariableItem re-render needlessly!
           * so we wrap `remove` with a ref for reducing redundant render
           */
          varRemoverRerf.current = remove;

          return (
            <div className={styled.var_list_row}>
              {/* 2 column layout */}
              <div className={styled.var_list_col}>
                {filteredItems
                  .filter((_, index) => index % 2 === 0)
                  .map((field) => (
                    <Form.Item
                      {...field}
                      key={'var-' + field.key}
                      noStyle
                      rules={[{ required: true, message: t('project.msg_var_name') }]}
                    >
                      <VariableItem
                        isCheck={isCheck}
                        path={field.field}
                        removerRef={varRemoverRerf}
                      />
                    </Form.Item>
                  ))}
              </div>

              <div className={styled.var_list_col}>
                {filteredItems
                  .filter((_, index) => index % 2 === 1)
                  .map((field) => (
                    <Form.Item
                      {...field}
                      key={'var-' + field.key}
                      noStyle
                      rules={[{ required: true, message: t('project.msg_var_name') }]}
                    >
                      <VariableItem
                        isCheck={isCheck}
                        path={field.field}
                        removerRef={varRemoverRerf}
                      />
                    </Form.Item>
                  ))}
              </div>

              {fields.length === 0 && (
                <NoResult
                  noImage
                  text={t('暂无变量，创建一个吧')}
                  style={{ margin: '50px auto 20px', width: '100%' }}
                />
              )}

              <div className={styled.add_button_row}>
                {/* DO NOT simplify `() => add()` to `add`, it will pollute form value with $event */}
                <Button
                  disabled={isCheck}
                  type="primary"
                  size="small"
                  icon={<Plus />}
                  onClick={() => add(giveDefaultVariable())}
                >
                  {t('workflow.btn_add_var')}
                </Button>
              </div>
            </div>
          );
        }}
      </Form.List>
    </>
  );
};

export default memo(VariableList);
