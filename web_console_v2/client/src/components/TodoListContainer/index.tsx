import React from 'react';
import styled from 'styled-components';
import { Button, Popover } from '@arco-design/web-react';

type TProps = {
  btnText: string;
  disabled: boolean;
  loading?: boolean;
  children: React.ReactNode;
  containerStyle?: React.CSSProperties;
};

const TodoButton = styled(Button)<{ disabled: boolean }>`
  background-color: ${(props) =>
    props.disabled ? 'var(--color-secondary)' : 'rgb(var(--arcoblue-1))'} !important;
  color: ${(props) =>
    props.disabled ? 'var(--color-text-3)' : 'rgb(var(--arcoblue-6))'} !important;
  z-index: 2;

  &[disabled] {
    cursor: not-allowed;
  }
`;

const Icon: React.FC<{ className?: string }> = ({ className }) => (
  <span className={className}>
    <svg fill="none" height="16" viewBox="0 0 16 16" width="16" xmlns="http://www.w3.org/2000/svg">
      <path
        clipRule="evenodd"
        d="m6.33301 1.93342c0-.1841-.14924-.33334-.33334-.33334h-.8372c-.1841 0-.33334.14924-.33334.33334l-.00033.66666h-1.82913c-.36819 0-.66666.31506-.66666.70371v9.25921c0 .3887.29847.7038.66666.7038h10.00003c.3682 0 .6666-.3151.6666-.7038v-9.25921c0-.38865-.2984-.70371-.6666-.70371l-1.8226-.0001v-.66667c0-.1841-.1492-.33333-.3333-.33333l-.84413.0001c-.18409 0-.33333.14924-.33333.33334v.66666h-3.33333zm3.54908 3.92573c.13001-.12997.34071-.12997.47071 0l.4706.47067c.13.12997.13.3407 0 .47067l-2.82176 2.82176-.00222.00225-.47067.4707c-.04998.05-.11192.0807-.17661.0923l-.03907.0046h-.0393c-.07851-.0046-.1557-.0369-.21568-.0969l-1.88267-1.88271c-.12998-.12997-.12998-.34069 0-.47067l.47066-.47066c.12997-.12998.3407-.12998.47067 0l1.17672 1.17664z"
        fill="currentColor"
        fillRule="evenodd"
      />
    </svg>
  </span>
);

const StyledIcon = styled(Icon)`
  position: relative;
  display: inline-block;
  top: 1px;
  margin-right: 10px;
`;

const TodoListContainer: React.FC<TProps> = ({
  btnText,
  loading,
  disabled,
  children,
  containerStyle,
}) => {
  const shouldDisabled = disabled && !loading;
  const btn = (
    <TodoButton loading={loading} disabled={shouldDisabled} style={containerStyle}>
      {!loading ? <StyledIcon /> : null}
      {btnText}
    </TodoButton>
  );
  if (shouldDisabled) {
    return btn;
  }

  return (
    <Popover
      getPopupContainer={() => window.document.body}
      content={children}
      position="br"
      style={{
        maxWidth: 1000,
      }}
    >
      {btn}
    </Popover>
  );
};

export default TodoListContainer;
