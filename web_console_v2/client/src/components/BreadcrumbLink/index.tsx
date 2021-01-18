import React, { FC } from 'react';
import styled from 'styled-components';
import { Breadcrumb } from 'antd';
import Slash from './Slash';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const Container = styled(Breadcrumb)`
  margin-bottom: 16px;
`;

type Props = {
  paths: {
    label: string;
    to?: string;
  }[];
};

const BreadcrumbLink: FC<Props> = ({ paths }) => {
  const { t } = useTranslation();

  return (
    <Container separator={<Slash />}>
      {paths.map((item, index) => (
        <Breadcrumb.Item>
          {index === paths.length - 1 ? t(item.label) : <Link to={item.to!}>{t(item.label)}</Link>}
        </Breadcrumb.Item>
      ))}
    </Container>
  );
};

export default BreadcrumbLink;
