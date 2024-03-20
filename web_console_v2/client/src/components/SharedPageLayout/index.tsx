import React, { FC } from 'react';
import styled from 'styled-components';
import { Tooltip, Card } from 'antd';
import GridRow from 'components/_base/GridRow';
import { QuestionCircle } from 'components/IconPark';
import defaultTheme from 'styles/_theme';

const PAGE_SECTION_PADDING = 20;

const Container = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  height: calc(100% - var(--contentOuterPadding));
  padding: 0 var(--contentOuterPadding);
`;
const PageHeader = styled.header`
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  padding: 0 20px;
  min-height: var(--pageHeaderHeight);
  max-height: var(--pageHeaderHeight);
  margin: 0 -${defaultTheme.contentOuterPadding} var(--contentOuterPadding);
  /* For showing sidebar's border */
  transform: translateX(1px);
  background-color: white;
  box-shadow: 0px 1px 0px var(--lineColor);
`;
const PageTitle = styled.h2`
  margin-bottom: 0;
  font-size: 14px;
  line-height: 22px;
`;
const Tip = styled(Tooltip)`
  line-height: 0;
`;
const PageSectionCard = styled(Card)`
  position: relative;
  display: grid;
  grid-auto-flow: row;
  margin-bottom: 10px;

  > .ant-card-body {
    display: flex;
    flex-direction: column;
    min-height: calc(
      100vh - var(--pageHeaderHeight) - var(--headerHeight) - var(--contentOuterPadding) * 2
    );
    background-color: inherit;
    padding: ${PAGE_SECTION_PADDING}px;

    > *:not(:last-child) {
      margin-bottom: 18px;
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
export const RemovePadding = styled.div`
  margin: -${PAGE_SECTION_PADDING}px -${PAGE_SECTION_PADDING}px 0;
`;
export const FormHeader = styled.h3`
  display: flex;
  height: 46px;
  font-size: 16px;
  line-height: 24px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--lineColor);
  margin: -${PAGE_SECTION_PADDING}px -${PAGE_SECTION_PADDING}px 0;
`;

interface Props {
  title: React.ReactNode;
  tip?: string;
  children?: React.ReactNode;
  contentWrapByCard?: boolean;
}

const SharedPageLayout: FC<Props> = ({ title, children, tip, contentWrapByCard = true }) => {
  return (
    <Container>
      <PageHeader>
        <GridRow gap="10">
          <PageTitle className="title">{title}</PageTitle>
          {tip && (
            <Tip title={tip} placement="rightBottom">
              <QuestionCircle />
            </Tip>
          )}
        </GridRow>
      </PageHeader>

      {contentWrapByCard ? <PageSectionCard>{children}</PageSectionCard> : children}
    </Container>
  );
};

export default SharedPageLayout;
