/* istanbul ignore file */

import React, { ReactNode, CSSProperties } from 'react';
import styled, { createGlobalStyle } from 'styled-components';

import { Menu, Popover, Tooltip } from '@arco-design/web-react';
import IconButton from 'components/IconButton';
import { More } from 'components/IconPark';

import { PopoverProps } from '@arco-design/web-react/es/Popover';

export const GLOBAL_CLASS_NAME = 'global-more-actions';

const GlobalStyle = createGlobalStyle`
  .${GLOBAL_CLASS_NAME} {
    min-width: 72px;
    border: 1px solid #e5e6e8;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
    border-radius: 4px;
    overflow: hidden;
    padding: 0;
    z-index: var(--zIndexLessThanModal);

    .arco-popover-content {
      padding: 0;
      .arco-popover-arrow {
        display: none !important;
      }
      .arco-popover-inner {
        border-radius: 0;
        .arco-popover-inner-content {
          padding: 6px 0;
        }
      }
    }
  }
`;

const ActionListContainer = styled(Menu)`
  .arco-menu-inner {
    margin: 0;
    padding: 0;
  }

  && .actionItem {
    width: 100%;
    min-height: 36px;
    text-align: center;
    margin: 0;
    padding: 0;

    .item {
      padding: 0 16px;
    }

    &:not(.arco-menu-disabled) {
      color: var(--fontColor, var(--textColor));
    }
  }
` as typeof Menu;

export interface ActionItem {
  /** Display Label */
  label: string;
  onClick?: () => void;
  /** Sometimes you need to disable the button */
  disabled?: boolean;
  /** Sometimes you want a hint when the button is disabled */
  disabledTip?: string;
  /** Danger button style, red color */
  danger?: boolean;
  /** Just for test */
  testId?: string;
}

export interface Props extends PopoverProps {
  /** DataSource */
  actionList: ActionItem[];
  /**
   * Customize content render
   */
  renderContent?: (actionList: ActionItem[]) => ReactNode;
  children?: any;
  zIndex?: number | string;
  className?: string | undefined;
}

function renderDefaultContent(actionList: ActionItem[]) {
  return (
    <ActionListContainer selectable={false}>
      {actionList.map((item, index) => (
        // Because "div" has no disable effect, replace div with "Menu.Item" here
        <Menu.Item
          className="actionItem"
          key={`${item.label}__${index}`}
          disabled={Boolean(item.disabled)}
          onClick={(event) => {
            event?.stopPropagation();
            item.onClick?.();
          }}
          style={
            {
              '--fontColor': item.danger ? 'var(--errorColor)' : null,
            } as CSSProperties
          }
        >
          {item.disabledTip && item.disabled ? (
            <Tooltip content={item.disabledTip}>
              <span className="item" data-testid={item.testId}>
                {item.label}
              </span>
            </Tooltip>
          ) : (
            <span className="item" data-testid={item.testId}>
              {item.label}
            </span>
          )}
        </Menu.Item>
      ))}
    </ActionListContainer>
  );
}

function MoreActions({
  actionList,
  trigger = 'click',
  children,
  renderContent,
  zIndex = 'var(--zIndexLessThanModal)',
  className,
  ...resetProps
}: Props) {
  return (
    <span onClick={(e) => e.stopPropagation()} className={className}>
      <GlobalStyle />
      <Popover
        content={renderContent ? renderContent(actionList) : renderDefaultContent(actionList)}
        position="bl"
        className={GLOBAL_CLASS_NAME}
        triggerProps={{
          trigger,
        }}
        style={{ zIndex: zIndex as any }}
        {...resetProps}
      >
        {children ?? <IconButton type="text" icon={<More />} data-testid="btn-more-actions" />}
      </Popover>
    </span>
  );
}

export default MoreActions;
