/* istanbul ignore file */

import i18n from 'i18n';
import React, { FunctionComponent } from 'react';
import styled from 'styled-components';
import { MixinCircle, MixinSquare } from 'styles/mixins';

const Container = styled.div`
  display: inline-flex;
  align-items: center;

  &::before {
    content: '';
    display: inline-block;
  }

  &::after {
    content: ${(props: Props) => (props.desc ? 'attr(data-desc)' : null)};
    padding-left: 5px;
  }
`;

const WritableShape = styled(Container)`
  &::before {
    width: 13px;
    height: 11px;
    background-color: var(--primaryColor);
    clip-path: polygon(50% 0, 100% 100%, 0 100%, 50% 0);
    transform: translateY(-0.5px);
  }
`;
const ReadableShape = styled(Container)`
  &::before {
    ${MixinSquare(11)};

    background-color: var(--successColor);
  }
`;
const PrivateShape = styled(Container)`
  &::before {
    ${MixinCircle(12)};

    background-color: var(--warningColor);
  }
`;

type Props = {
  /**
   * Enable desc
   * @default false
   */
  desc?: boolean;
  /** Desc prefix */
  prefix?: string;
  /** Container style */
  style?: React.CSSProperties;
};

const Writable: FunctionComponent<Props> = (props) => {
  return (
    <WritableShape
      {...props}
      data-desc={i18n.t('workflow.var_auth_write', { prefix: props.prefix })}
    />
  );
};

const Readable: FunctionComponent<Props> = (props) => {
  return (
    <ReadableShape
      {...props}
      data-desc={i18n.t('workflow.var_auth_read', { prefix: props.prefix })}
    />
  );
};

const Private: FunctionComponent<Props> = (props) => {
  return (
    <PrivateShape
      {...props}
      data-desc={i18n.t('workflow.var_auth_private', { prefix: props.prefix })}
    />
  );
};

const VariablePermission = { Writable, Readable, Private };

const LegendContainer = styled.div`
  position: relative;
  display: flex;
  flex-wrap: wrap;
  padding: 7px 16px;
  border-radius: 2px;
  background-color: rgb(var(--gray-1));

  > div:not(:last-of-type) {
    margin-right: 30px;
  }
`;

export const VariablePermissionLegend: FunctionComponent<Props> = ({ style, ...restProps }) => {
  return (
    <LegendContainer style={style}>
      <Writable {...restProps} />
      <Readable {...restProps} />
      <Private {...restProps} />
    </LegendContainer>
  );
};

export default VariablePermission;
