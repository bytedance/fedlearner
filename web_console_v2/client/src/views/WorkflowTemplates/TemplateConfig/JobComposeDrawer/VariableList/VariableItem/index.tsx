import {
  Form,
  Button,
  Radio,
  Tooltip,
  Message,
  Dropdown,
  Popconfirm,
  Input,
} from '@arco-design/web-react';
import { IconLink, IconDelete, IconDown } from '@arco-design/web-react/icon';
import PrettyMenu, { PrettyMenuItem } from 'components/PrettyMenu';
import { indicators } from 'components/VariableLabel';
import VariablePermission from 'components/VariblePermission';
import { useSubscribe } from 'hooks';
import React, {
  ChangeEvent,
  FC,
  memo,
  useContext,
  useRef,
  useState,
  useMemo,
  useCallback,
} from 'react';
import { useToggle } from 'react-use';
import styled from './index.module.less';
import { ValidateErrorEntity } from 'typings/component';
import { Variable, VariableAccessMode, VariableComponent } from 'typings/variable';
import { VariableDefinitionForm } from 'views/WorkflowTemplates/TemplateForm/stores';
import { Container, Details, Name, Summary } from '../../elements';
import {
  ComposeDrawerContext,
  COMPOSE_DRAWER_CHANNELS,
  HighlightPayload,
  scrollDrawerBodyTo,
} from '../../index';
import SlotLinkAnchor, { collectSlotLinks, SlotLink } from './SlotLinkAnchor';
import WidgetSchema from './WidgetSchema';

export const disabeldPeerWritableComponentTypeList = [
  VariableComponent.DatasetPath,
  VariableComponent.AlgorithmSelect,
  VariableComponent.FeatureSelect,
];

type Props = {
  path: string;
  isCheck?: boolean;
  value?: VariableDefinitionForm;
  onChange?: (val: VariableDefinitionForm) => any;
  remover?: any;
  removerRef?: any;
};

const VariableItem: FC<Props> = ({ path, isCheck, value, removerRef }) => {
  const ref = useRef<HTMLDetailsElement>(null);
  const [isOpen, toggleOpen] = useToggle(_shouldInitiallyOpen(value));
  const [hasError, toggleError] = useToggle(false);
  const [slotLinks, setSlotLinks] = useState<SlotLink[]>([]);
  const [highlighted, setHighlight] = useToggle(false);

  const context = useContext(ComposeDrawerContext);
  const varsIdentifyStr = context.formData?.variables?.map((item) => item.name).join();

  const duplicatedNameValidator = useCallback(
    (value: any, callback: (error?: string) => void) => {
      if (
        context.formData?.variables
          .filter((item) => item._uuid !== data._uuid)
          .some((item) => item.name === value)
      ) {
        callback('检测到重名变量');
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [varsIdentifyStr],
  );

  useSubscribe(
    COMPOSE_DRAWER_CHANNELS.broadcast_error,
    (_: string, errInfo: ValidateErrorEntity) => {
      const hasError = errInfo.errorFields.some((field) => {
        const [pathL1] = field.name;
        return pathL1 === path;
      });

      toggleError(hasError);

      if (hasError) {
        toggleOpen(true);
      }
    },
  );
  useSubscribe(COMPOSE_DRAWER_CHANNELS.highlight, (_: string, { varUuid }: HighlightPayload) => {
    if (value && varUuid === value._uuid) {
      setHighlight(true);
      toggleOpen(true);

      // Scroll slot into view
      const verticalMiddleY = (window.innerHeight - 60) / 2;
      const top = ref.current?.offsetTop || verticalMiddleY;
      scrollDrawerBodyTo(top - verticalMiddleY);

      setTimeout(() => {
        setHighlight && setHighlight(false);
      }, 5000);
    }
  });

  const widtgetSchemaPath = useMemo(() => {
    return [path, 'widget_schema'];
  }, [path]);

  if (!value) {
    return null;
  }

  const data = value;
  const varName = data.name;

  const PermissionIndicator = indicators[data.access_mode];
  const actionDisabled = !varName;

  const componentType = data?.widget_schema?.component;

  return (
    <Details data-has-error={hasError} ref={ref as any} data-open={isOpen}>
      <Summary
        data-has-error={hasError}
        data-highlighted={highlighted}
        onClick={(evt: any) => onToggle(evt as any)}
      >
        {/*
            Certain HTML elements, like <summary>, <fieldset> and <button>, do not work as flex containers.
            You can work by nesting a div under your summary
            https://stackoverflow.com/questions/46156669/safari-flex-item-unwanted-100-width-css/46163405
        */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            height: '100%',
          }}
        >
          <PermissionIndicator />

          <Name className={styled.var_name}>{varName}</Name>
          <StopClickPropagation>
            <div>
              {context.isEasyMode && (
                <Dropdown
                  trigger={['click']}
                  position="bl"
                  disabled={isCheck}
                  droplist={
                    <PrettyMenu style={{ width: 'auto' }}>
                      {slotLinks.map((link, index) => (
                        <PrettyMenuItem key={link.jobUuid + index}>
                          <SlotLinkAnchor link={link} />
                        </PrettyMenuItem>
                      ))}
                      {slotLinks.length === 0 && (
                        <PrettyMenuItem key="variable">
                          <small className={styled.no_link}>该变量暂未被引用</small>
                        </PrettyMenuItem>
                      )}
                    </PrettyMenu>
                  }
                >
                  <Tooltip content={actionDisabled ? '没有变量名无法查看引用' : ''}>
                    <Button
                      className={styled.action_button}
                      type="text"
                      size="small"
                      disabled={actionDisabled}
                      icon={<IconLink />}
                      onClick={inspectSlotLinks}
                    >
                      查看引用
                    </Button>
                  </Tooltip>
                </Dropdown>
              )}
              <StopClickPropagation>
                <Popconfirm disabled={isCheck} title="确认删除该变量吗" onOk={onRemoveClick as any}>
                  <Button
                    className={styled.action_button}
                    disabled={isCheck}
                    type="text"
                    size="small"
                    icon={<IconDelete />}
                  >
                    删除
                  </Button>
                </Popconfirm>
              </StopClickPropagation>

              <IconDown className={styled.open_indicator} />
            </div>
          </StopClickPropagation>
        </div>
      </Summary>
      <Container style={{ display: isOpen ? 'block' : 'none' }}>
        <Form.Item
          field={[path, 'name'].join('.')}
          label="Key"
          rules={[
            { required: true, message: '请输入变量 Key' },
            {
              match: /^[a-zA-Z_0-9-]+$/g,
              message: '只允许大小写英文字母数字及下划线的组合',
            },
            {
              validator: duplicatedNameValidator,
            },
          ]}
        >
          <Input disabled={isCheck} placeholder="请输入变量名 （仅允许英语及下划线)" />
        </Form.Item>

        <Form.Item
          field={[path, 'access_mode'].join('.')}
          label="对侧权限"
          rules={[{ required: true }]}
        >
          <Radio.Group disabled={isCheck} type="button">
            <Radio
              value={VariableAccessMode.PEER_WRITABLE}
              disabled={disabeldPeerWritableComponentTypeList.includes(componentType!)}
            >
              <VariablePermission.Writable desc />
            </Radio>
            <Radio value={VariableAccessMode.PEER_READABLE}>
              <VariablePermission.Readable desc />
            </Radio>
            <Radio value={VariableAccessMode.PRIVATE}>
              <VariablePermission.Private desc />
            </Radio>
          </Radio.Group>
        </Form.Item>

        <Form.Item field={widtgetSchemaPath.join('.')} noStyle>
          <WidgetSchema isCheck={isCheck} form={context.formInstance!} path={widtgetSchemaPath} />
        </Form.Item>
      </Container>
    </Details>
  );

  function onRemoveClick() {
    if (context.isEasyMode) {
      const refSrcs = collectSlotLinks(context.uuid, data._uuid, context);
      if (refSrcs.length) {
        Message.warning('变量仍然被引用，请先解除引用关系');
        setSlotLinks(refSrcs);
        return;
      }
    }
    if (!path) return;

    removerRef.current?.(Number(path.slice(path.indexOf('[') + 1, -1)));
  }
  function onToggle(evt: ChangeEvent<HTMLDetailsElement>) {
    toggleOpen(evt.target.open);
  }
  function inspectSlotLinks() {
    const refSrcs = collectSlotLinks(context.uuid, data._uuid, context);
    setSlotLinks(refSrcs);
  }
};

function _shouldInitiallyOpen(val: Variable | undefined) {
  if (!val) return false;

  return !val.name;
}

function StopClickPropagation({ children }: { children: React.ReactNode }) {
  return <span onClick={(evt) => evt.stopPropagation()}>{children}</span>;
}

export default memo(VariableItem);
