/* istanbul ignore file */

import React, { FC } from 'react';
import styled from 'styled-components';
import illustration from 'assets/images/empty.svg';
import model from 'assets/images/empty-data.svg';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { convertToUnit } from 'shared/helpers';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: ${(props: Pick<Props, 'width'>) => (props.width ? convertToUnit(props.width) : '15%')};
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
  color: var(--textColorSecondary);
`;

const Img = styled.img`
  display: block;
  width: 60px;
  margin-bottom: 20px;
  pointer-events: none;
  user-select: none;
`;

type Props = {
  text: string;
  noImage?: boolean;
  CTAText?: string; // call to action text
  to?: string;
  src?: string;
  width?: any;
};

type NoModelVersionResultProps = Partial<Props>;

/**
 * Common no result placeholder
 * NOTE: make sure you put inside a grid or flex container!
 */
const NoResult: FC<Props> & {
  ModelVersion: FC<NoModelVersionResultProps>;
  NoData: FC<any>;
} = ({ text, CTAText, to, noImage, src = illustration, ...props }) => {
  const { t } = useTranslation();
  return (
    <Container {...props}>
      {!noImage && <Illustration src={illustration} />}
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

const NoModelVersionResult: FC<NoModelVersionResultProps> = ({
  text,
  CTAText,
  to = '/model-center/model-management/sender/create/global',
  src = model,
  ...props
}) => {
  const { t } = useTranslation();
  return (
    <Container {...props}>
      <Img src={src} />
      <Text>
        <span>{text || t('model_center.no_result')}</span>

        {to && <Link to={to}>{CTAText || t('model_center.btn_train_model')}</Link>}
      </Text>
    </Container>
  );
};

const NoData = () => {
  const { t } = useTranslation();

  return (
    <div className="arco-empty">
      <div className="arco-empty-wrapper">
        <div className="arco-empty-image">
          <svg
            width="60"
            height="60"
            viewBox="0 0 60 60"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M45.9298 24.0005C46.2641 24.0005 46.5764 24.1676 46.7618 24.4458L53.1316 34.0005H6.86865L13.2385 24.4458C13.4239 24.1676 13.7362 24.0005 14.0705 24.0005H45.9298Z"
              stroke="#C2C6CC"
              strokeWidth="2"
            />
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M55 35.0006V47.0006C55 49.2097 53.2091 51.0006 51 51.0006H9C6.79086 51.0006 5 49.2097 5 47.0006V35.0006L24.083 35.0002C24.0284 35.3256 24 35.6597 24 36.0006C24 39.3143 26.6863 42.0006 30 42.0006C33.3137 42.0006 36 39.3143 36 36.0006C36 35.6597 35.9716 35.3256 35.917 35.0002L55 35.0006Z"
              fill="#C2C6CC"
            />
            <path
              d="M32 10.0005C32 9.4482 31.5523 9.00049 31 9.00049C30.4477 9.00049 30 9.4482 30 10.0005V16.0005C30 16.5528 30.4477 17.0005 31 17.0005C31.5523 17.0005 32 16.5528 32 16.0005V10.0005Z"
              fill="#C2C6CC"
            />
            <path
              d="M15.5857 11.1718C15.1952 10.7813 14.562 10.7813 14.1715 11.1718C13.7809 11.5623 13.7809 12.1955 14.1715 12.586L18.4141 16.8287C18.8046 17.2192 19.4378 17.2192 19.8283 16.8287C20.2188 16.4381 20.2188 15.805 19.8283 15.4144L15.5857 11.1718Z"
              fill="#C2C6CC"
            />
            <path
              d="M46.4141 11.1718C46.8046 10.7813 47.4378 10.7813 47.8283 11.1718C48.2188 11.5623 48.2188 12.1955 47.8283 12.586L43.5857 16.8287C43.1951 17.2192 42.562 17.2192 42.1714 16.8287C41.7809 16.4381 41.7809 15.805 42.1714 15.4144L46.4141 11.1718Z"
              fill="#C2C6CC"
            />
          </svg>
        </div>
        <div className="arco-empty-description">{t('no_data')}</div>
      </div>
    </div>
  );
};

NoResult.ModelVersion = NoModelVersionResult;
NoResult.NoData = NoData;

export default NoResult;
