import React, { FC } from 'react';
import styled from 'styled-components';
import GridRow from '../GridRow';
import { MixinCircle } from 'styles/mixins';

const Container = styled.div`
  display: flex;
`;
const Block = styled.div`
  flex: 1;
  padding: 9px 11px;
  border: 1.5px solid var(--border-color, var(--lineColor));
  border-radius: 2px;
  cursor: pointer;

  &[data-is-active='true'] {
    --label-color: var(--primaryColor);
    --label-weight: 500;
    --border-color: var(--primaryColor);
  }

  &[data-is-disabled='true'] {
    cursor: not-allowed;
    filter: grayscale(50);
  }

  & + & {
    margin-left: 16px;
  }
`;
const Label = styled.label`
  font-size: 12px;
  line-height: 20px;
  color: var(--label-color, var(--textColorStrong));
  font-weight: var(--label-weight, normal);
`;

const RadioIcon = styled.div`
  ${MixinCircle(14)}
  border: 2px solid var(--border-color, var(--gray4));

  &[data-is-active='true'] {
    --border-color: var(--primaryColor);
    border-width: 4px;
  }
`;

type Option = { value: any; label: string; disabled?: boolean };

type Props = {
  value?: any;
  onChange?: (val: any) => void;
  options: Option[];
  renderBlockInner?: (
    props: Option,
    options: { label: React.ReactNode; isActive: boolean },
  ) => React.ReactElement;
};

const BlockRadio: FC<Props> = ({ value, onChange, options, renderBlockInner }) => {
  return (
    <Container>
      {options.map((item) => {
        return (
          <Block
            data-is-active={value === item.value}
            data-is-disabled={item.disabled}
            onClick={() => onBlockClick(item)}
          >
            {renderBlockInner ? (
              renderBlockInner(item, {
                label: <Label>{item.label}</Label>,
                isActive: value === item.value,
              })
            ) : (
              <GridRow gap="12">
                <RadioIcon data-is-active={value === item.value} />
                <Label>{item.label}</Label>
              </GridRow>
            )}
          </Block>
        );
      })}
    </Container>
  );

  function onBlockClick(item: Option) {
    if (item.disabled) return;

    onChange && onChange(item.value);
  }
};

export default BlockRadio;
