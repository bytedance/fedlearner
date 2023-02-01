import React, { FC, useMemo } from 'react';
import styled, { CSSProperties } from 'styled-components';
import { Tooltip } from '@arco-design/web-react';
import TitleWithIcon from 'components/TitleWithIcon';
import { IconInfoCircle } from '@arco-design/web-react/icon';
import GridRow from '../GridRow';

const baseGap = 16;

const Container = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  margin-right: -${(props: Partial<Props>) => props.gap || baseGap}px;
  margin-bottom: -${(props: Partial<Props>) => props.gap || baseGap}px;
  flex-direction: ${(props: Partial<Props>) => (props.isVertical ? 'column' : 'row')};
`;
const Block = styled.div`
  --border-color: transparent;

  display: flex;
  flex: 1 0 auto;
  align-items: center;
  justify-content: ${(props: Partial<Props>) => (props.isCenter ? 'center' : 'normal')};
  flex-grow: var(--flex-grow, 1);
  min-height: 32px;
  padding: 0 12px;
  width: ${(props: Partial<Props>) =>
    props.blockItemWidth ? `${props.blockItemWidth}px` : 'auto'};
  margin-right: ${(props: Partial<Props>) => props.gap || baseGap}px;
  margin-bottom: ${(props: Partial<Props>) => props.gap || baseGap}px;
  border: 1.5px solid var(--border-color, var(--lineColor));
  border-radius: 4px;
  cursor: pointer;
  background-color: var(--bg-color, var(--componentBackgroundColorGray));

  &:hover {
    --label-color: var(--primaryColor);
  }

  &[data-is-active='true'] {
    --label-color: var(--primaryColor);
    --border-color: var(--primaryColor);
    --label-weight: 500;
    --bg-color: #fff;
  }

  &[data-is-disabled='true'] {
    cursor: not-allowed;
    --label-color: var(--textColorDisabled);
  }

  &[data-is-active='true'][data-is-disabled='true'] {
    --label-color: initial;
    --border-color: initial;
    --label-weight: initial;
    --bg-color: #fff;
  }
`;
const ContainerOneHalf = styled.div`
  display: flex;
  flex: 1;
`;
const BlockOneHalf = styled.div`
  --border-color: transparent;
  display: flex;
  flex: 1;
  min-height: 32px;
  padding: 0 12px;
  border: 1.5px solid var(--border-color, var(--lineColor));
  border-radius: 4px;
  cursor: pointer;
  background-color: var(--bg-color, var(--componentBackgroundColorGray));
  justify-content: ${(props: Partial<Props>) => (props.isCenter ? 'center' : 'normal')};
  align-items: center;

  &[data-is-active='true'] {
    --label-color: var(--primaryColor);
    --border-color: var(--primaryColor);
    --label-weight: 500;
    --bg-color: #fff;
  }

  &[data-is-disabled='true'] {
    cursor: not-allowed;
    --label-color: var(--textColorDisabled);
  }

  &[data-is-active='true'][data-is-disabled='true'] {
    --label-color: initial;
    --border-color: initial;
    --label-weight: initial;
    --bg-color: #fff;
  }

  & + & {
    margin-left: ${(props: Partial<Props>) => props.gap || baseGap}px;
  }
`;

const Label = styled.label`
  font-size: 12px;
  color: var(--label-color, var(--textColorStrong));
  font-weight: var(--label-weight, normal);
  cursor: inherit;
`;
const LabelTips = styled(Label)`
  font-weight: normal;
  font-size: 12px;
  color: var(--label-color, var(--textColorSecondary));
`;

const ContainerWithTips = styled.div`
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: space-between;
  height: 100%;
`;

type Option = {
  /** Form value */
  value: any;
  /** Display label */
  label: string;
  disabled?: boolean;
  /** Extra data, one of the function(renderBlockInner) arguments */
  data?: any;
  /** Extra tip, only work in <BlockRadio.WithTip/> options */
  tip?: string;
  /** Extra tip, only work in <BlockRadio.WithTooltip/> options */
  tooltip?: string;
  warnTip?: string;
};

type Props = {
  value?: any;
  onChange?: (val: any) => void;
  /**
   * DataSource
   */
  options: Option[];
  /**
   * Gap between items
   */
  gap?: number;
  /**
   * flex-grow
   */
  flexGrow?: number;
  /**
   * When beforeChange return false or Promise that is resolved false, don't call onChange function next time
   */
  beforeChange?: (val: any) => boolean | Promise<boolean>;
  /**
   * Customize children render
   */
  renderBlockInner?: (
    props: Option,
    options: { label: React.ReactNode; isActive: boolean; data?: any },
  ) => React.ReactElement;
  /**
   * All items disabled
   */
  disabled?: boolean;
  /**
   * Inline text center
   */
  isCenter?: boolean;
  isVertical?: boolean;
  isOneHalfMode?: boolean;
  isWarnTip?: boolean;
  blockItemWidth?: number;
};

const BlockRadio: FC<Props> & {
  WithTip: React.FC<Props>;
  WithToolTip: React.FC<Props>;
} = ({
  gap = baseGap,
  flexGrow = 1,
  value,
  beforeChange,
  onChange,
  options,
  renderBlockInner,
  disabled = false,
  isVertical = false,
  isCenter = false,
  isOneHalfMode = false,
  isWarnTip = false,
  blockItemWidth = 0,
}) => {
  const warnTip = useMemo(() => {
    return options.find((item) => item.value === value)?.warnTip;
  }, [value, options]);
  if (isOneHalfMode) {
    return (
      <ContainerOneHalf>
        {options.map((item) => {
          return (
            <BlockOneHalf
              data-is-active={value === item.value}
              data-is-disabled={disabled || item.disabled}
              key={item.value}
              onClick={() => onBlockClick(item)}
              isCenter={isCenter}
              gap={gap}
            >
              {renderBlockInner ? (
                renderBlockInner(item, {
                  label: <Label>{item.label}</Label>,
                  data: item.data,
                  isActive: value === item.value,
                })
              ) : (
                <Label>{item.label}</Label>
              )}
            </BlockOneHalf>
          );
        })}
      </ContainerOneHalf>
    );
  }

  return (
    <Container isVertical={isVertical} gap={gap}>
      {options.map((item) => {
        return (
          <Block
            data-is-active={value === item.value}
            data-is-disabled={disabled || item.disabled}
            key={item.value}
            style={{ '--flex-grow': flexGrow } as CSSProperties}
            onClick={() => onBlockClick(item)}
            isCenter={isCenter}
            blockItemWidth={blockItemWidth}
            gap={gap}
            role="radio"
          >
            {renderBlockInner ? (
              renderBlockInner(item, {
                label: <Label>{item.label}</Label>,
                data: item.data,
                isActive: value === item.value,
              })
            ) : (
              <GridRow gap="12">
                <Label>{item.label}</Label>
              </GridRow>
            )}
          </Block>
        );
      })}
      {isWarnTip && warnTip && (
        <TitleWithIcon title={warnTip} isLeftIcon={true} isShowIcon={true} icon={IconInfoCircle} />
      )}
    </Container>
  );

  async function onBlockClick(item: Option) {
    if (disabled || item.disabled || item.value === value) return;

    if (beforeChange) {
      const shouldChange = beforeChange(item.value);

      if (!(await shouldChange)) {
        return;
      }
    }
    onChange && onChange(item.value);
  }
};

const WithTip: FC<Props> = (props) => {
  return (
    <BlockRadio
      renderBlockInner={(item, { label, isActive }) => {
        return (
          <ContainerWithTips>
            <Label>{item.label}</Label>
            <LabelTips>{item.tip}</LabelTips>
          </ContainerWithTips>
        );
      }}
      {...props}
    />
  );
};
const WithToolTip: FC<Props> = (props) => {
  return (
    <BlockRadio
      renderBlockInner={(item) => {
        return (
          <Tooltip content={item.tooltip}>
            <Label>{item.label}</Label>
          </Tooltip>
        );
      }}
      {...props}
    />
  );
};
BlockRadio.WithTip = WithTip;
BlockRadio.WithToolTip = WithToolTip;

export default BlockRadio;
