import React, { FC } from 'react';
import styled from 'styled-components';
import illustration from 'assets/images/empty.svg';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 15%;
  min-width: 100px;
  margin: auto;
`;
const Illustration = styled.img`
  display: block;
  width: 100%;
  margin-bottom: 20px;
  pointer-events: none;
  user-select: none;
`;
const Text = styled.span`
  font-size: 14px;
  white-space: nowrap;
`;

type Props = {
  text: string;
  CTAText?: string; // call to action text
  to?: string;
};

/**
 * Common no result placeholder
 * NOTE: make sure you put inside a grid or flex container!
 */
const NoResult: FC<Props> = ({ text, CTAText, to, ...props }) => {
  const { t } = useTranslation();
  return (
    <Container {...props}>
      <Illustration src={illustration} />
      <Text>
        <span>{text}</span>

        {to && (
          <>
            <span>, </span>
            <Link to={to}>{CTAText || t('app.go_create')}</Link>
          </>
        )}
      </Text>
    </Container>
  );
};

export default NoResult;
