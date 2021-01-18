import React, { FC } from 'react';
import styled from 'styled-components';
import { Tooltip, Card } from 'antd';
import GridRow from 'components/_base/GridRow';
import { QuestionCircle } from 'components/IconPark';

const Container = styled(Card)`
  // header height: 60px; content padding: 6px;
  height: calc(100vh - 60px - 16px * 2);

  > .ant-card-body {
    display: flex;
    flex-direction: column;
    gap: 18px;
    height: 100%;
    padding: 22px 24px;

    @supports (gap: 18px) {
      gap: 18px;
    }
    @supports not (gap: 18px) {
      > *::not(::last-child) {
        margin-bottom: 18px;
      }
    }

    &::before {
      content: none;
    }
  }

  .title-question {
    width: 16px;
    height: 16px;
  }
`;
const ListTitle = styled.h2`
  margin-bottom: 0;
  font-size: 20px;
  line-height: 28px;
`;
const Tip = styled(Tooltip)`
  line-height: 0;
`;

interface Props {
  title: string;
  children?: React.ReactNode;
  tip?: string;
}

const ListPageCard: FC<Props> = ({ title, children, tip }) => {
  return (
    <Container>
      <GridRow gap="10">
        <ListTitle className="title">{title}</ListTitle>

        {tip && (
          <Tip title={tip} placement="rightBottom">
            <QuestionCircle />
          </Tip>
        )}
      </GridRow>

      {children}
    </Container>
  );
};

export default ListPageCard;
