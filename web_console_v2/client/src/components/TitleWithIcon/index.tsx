/* istanbul ignore file */
import React, { FC, CSSProperties } from 'react';
import styled from 'styled-components';
import { Tooltip, Space } from '@arco-design/web-react';
import { InfoCircleFill } from 'components/IconPark';

const Container = styled.div<{
  $isBlock?: boolean;
}>`
  display: ${(props) => (props.$isBlock ? 'block' : 'inline-block')};
`;
const Label = styled.span`
  display: inline-block;
  font-size: 12px;
  color: var(--color, --textColor);
`;

const IconContainer = styled.span`
  display: inline-block;
`;
const LeftIconContainer = styled.span`
  display: inline-block;
  margin-right: 5px;
`;

const DefaultIcon = styled(InfoCircleFill)`
  color: #86909c;
`;

export type Props = {
  className?: string;
  /** Display title */
  title: string | React.ReactNode;
  /** Custom icon */
  icon?: any;
  /** Tooptip tip */
  tip?: string;
  /**  Icon on the left of title */
  isLeftIcon?: boolean;
  isShowIcon?: boolean;
  textColor?: string;
  /** Is container display: block, otherwise inline-block */
  isBlock?: boolean;
};

const TitleWithIcon: FC<Props> = ({
  className,
  title,
  tip,
  icon = DefaultIcon,
  isLeftIcon = false,
  isShowIcon = false,
  isBlock = true,
  textColor,
}) => {
  if (isLeftIcon) {
    return (
      <Container
        className={className}
        $isBlock={isBlock}
        style={
          textColor
            ? ({
                '--color': textColor,
              } as CSSProperties)
            : {}
        }
      >
        {isShowIcon && (
          <LeftIconContainer>
            <Tooltip content={tip}>{React.createElement(icon)}</Tooltip>
          </LeftIconContainer>
        )}
        <Label>{title}</Label>
      </Container>
    );
  }

  return (
    <Container
      className={className}
      $isBlock={isBlock}
      style={
        textColor
          ? ({
              '--color': textColor,
            } as CSSProperties)
          : {}
      }
    >
      <Space>
        <Label>{title}</Label>
        {isShowIcon && (
          <IconContainer>
            <Tooltip content={tip}>{React.createElement(icon)}</Tooltip>
          </IconContainer>
        )}
      </Space>
    </Container>
  );
};

export default TitleWithIcon;
