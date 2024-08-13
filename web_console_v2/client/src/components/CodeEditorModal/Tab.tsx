import React, { FC } from 'react';
import styled from 'styled-components';
import { Tooltip } from '@arco-design/web-react';

import { MixinEllipsis } from 'styles/mixins';

import { Close } from 'components/IconPark';

const IconContainer = styled.div`
  display: inline-block;
  margin-right: 8px;
  overflow: hidden;
`;
const Name = styled.div`
  ${MixinEllipsis(80, '%')}
  display: inline-block;
  font-size: 12px;
  font-weight: 400;
  color: var(--font-color);
`;
const StyledClose = styled(Close)`
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
`;

const Container = styled.div`
  --bg-color: #f2f3f8;
  --bg-color-active: #fff;
  --icon-color: #86909c;
  --icon-color-active: #468dff;
  --font-color: #1d2129;
  --border-color: #e5e8ee;
  --border-color-active: #1678ff;

  position: relative;
  display: inline-block;
  height: 36px;
  line-height: 36px;
  padding: 0 32px 0 12px;

  min-width: 80px;
  max-width: 200px;
  background-color: var(--bg-color);
  border-right: 1px solid var(--border-color);
  border-bottom: 1px solid transparent;
  cursor: pointer;

  &[data-is-active='true'] {
    background-color: var(--bg-color-active);
    border-bottom: 1px solid var(--border-color-active);

    ${IconContainer} {
      color: var(--icon-color-active);
    }
    ${Name} {
      font-weight: 500;
    }
  }
`;

type Props = {
  theme?: string;
  isActive?: boolean;
  icon?: React.ReactNode;
  fileName?: string;
  fullPathFileName?: string;
  onClick?: () => void;
  onClose?: () => void;
};

const Tab: FC<Props> = ({
  theme,
  isActive = false,
  icon,
  fileName = '',
  fullPathFileName = '',
  onClick,
  onClose,
}) => {
  return (
    <Tooltip content={fullPathFileName || fileName}>
      <Container
        data-is-active={isActive}
        data-theme={theme}
        onClick={onClick}
        data-testid={`tab-${fullPathFileName || fileName}`}
      >
        {icon && <IconContainer>{icon}</IconContainer>}
        <Name>{fileName || ''}</Name>
        <StyledClose
          data-testid={`tab-btn-close-${fullPathFileName || fileName}`}
          onClick={(event) => {
            event.stopPropagation();
            onClose && onClose();
          }}
        />
      </Container>
    </Tooltip>
  );
};

export default Tab;
