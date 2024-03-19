/* istanbul ignore file */

import React, { FC, useEffect, useState } from 'react';
import styled from 'styled-components';
import { useRecoilState, useRecoilValue } from 'recoil';
import i18n from 'i18n';

import { appFlag, appState } from 'stores/app';

import { Tooltip, Card, Button, Message, Space } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';
import { QuestionCircle } from 'components/IconPark';
import TitleWithIcon from 'components/TitleWithIcon';
import { FlagKey } from 'typings/flag';

export const PAGE_SECTION_PADDING = 20;
export const PAGE_FIXED_BOTTOM_LAYOUT_HEIGHT = 64;
export const PAGE_HEADER_Z_INDEX = 6;

const Container = styled.div<{ isHideHeader?: boolean }>`
  ${(props) =>
    props.isHideHeader &&
    `
      --pageHeaderHeight:0px;
      padding-top: var(--contentOuterPadding) !important;
    `};

  position: relative;
  display: flex;
  flex-direction: column;
  height: calc(100% - var(--contentOuterPadding));
  padding: 0 var(--contentOuterPadding);
`;
const PageHeader = styled.header`
  --horizontalPadding: 20px;
  position: sticky;
  top: 0;
  z-index: ${PAGE_HEADER_Z_INDEX};
  display: flex;
  align-items: center;
  padding: 0 var(--horizontalPadding);
  min-height: var(--pageHeaderHeight);
  max-height: var(--pageHeaderHeight);
  margin: 0 calc(0px - var(--contentOuterPadding)) var(--contentOuterPadding);
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
const PageCenterTitle = styled.span`
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: inline-block;
  color: var(--textColorStrong);
  font-size: 16px;
  font-weight: 500;
`;
const PageRightTitle = styled.div`
  position: absolute;
  top: 50%;
  right: var(--horizontalPadding);
  transform: translateY(-50%);
`;
const Tip = styled(Tooltip)`
  line-height: 0;
`;
export const PageSectionCard = styled(Card)<{
  $cardPadding?: number;
  $isNestSpinFlexContainer?: boolean;
}>`
  position: relative;
  display: grid;
  grid-auto-flow: row;
  margin-bottom: 10px;
  font-size: 12px;
  > .arco-card-body {
    display: flex;
    flex-direction: column;
    /* --SidebarWidth comes from AppLayout element in views/index.tsx */
    width: calc(100vw - var(--contentOuterPadding) * 2 - var(--SidebarWidth));
    max-width: calc(100vw - var(--contentOuterPadding) * 2 - var(--SidebarWidth));
    min-width: calc(100vw - var(--contentOuterPadding) * 2 - var(--SidebarWidth));
    min-height: calc(
      100vh - var(--pageHeaderHeight) - var(--headerHeight) - var(--contentOuterPadding) * 2
    );
    background-color: inherit;
    padding: ${(props) => props.$cardPadding}px;
    overflow-x: hidden;

    > *:not(:last-child) {
      margin-bottom: 18px;
    }

    > [data-auto-fill] {
      flex: 1;
    }

    &::before {
      content: none;
    }

    ${(props) =>
      props.$isNestSpinFlexContainer &&
      `
        > .arco-spin {
          height: 100%;
          .arco-spin-children {
            display: flex;
            flex-direction: column;
            height: 100%;
          }
        }
    `};
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

const FixedBottomContainer = styled.div`
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  min-height: ${PAGE_FIXED_BOTTOM_LAYOUT_HEIGHT}px;
  max-height: ${PAGE_FIXED_BOTTOM_LAYOUT_HEIGHT}px;
  margin: var(--contentOuterPadding) calc(0px - var(--contentOuterPadding)) 0;
  background-color: #fff;
  padding: 0 var(--contentOuterPadding);
  box-shadow: 0px -2px 4px rgba(26, 34, 51, 0.08);
  border-radius: 2px;

  button {
    margin-right: 12px;
  }
`;

interface Props {
  /**
   * Title on left
   */
  title?: React.ReactNode;
  /**
   * Title on center
   */
  centerTitle?: React.ReactNode;
  /**
   * Title on right
   */
  rightTitle?: React.ReactNode;
  /**
   * Tooptip display text with <QuestionCircle/> icon
   */
  tip?: string;
  contentWrapByCard?: boolean;
  cardPadding?: number;
  /**
   * Enable <Spin/> height:100% style
   */
  isNestSpinFlexContainer?: boolean;
  /**
   * @deprecated is Hide siderbar
   *
   */
  removeSidebar?: boolean;
  isHideHeader?: boolean;
  /** Is show fixed bottom layout */
  isShowFixedBottomLayout?: boolean;
  isNeedHelp?: boolean;
  /** Render custom fixed bottom layout  */
  renderFixedBottomLayout?: () => React.ReactNode;
  /** Fixed bottom layout ok text */
  bottomOkText?: string;
  /** Fixed bottom layout cancel text */
  bottomCancelText?: string;
  /** Fixed bottom layout tip */
  bottomTip?: string;
  /** Fixed bottom layout ok button loading */
  bottomOkButtonIsLoading?: boolean;
  /** Fixed bottom layout ok button loading */
  bottomCancelButtonIsLoading?: boolean;
  onBottomOkClick?: () => void | Promise<void>;
  onBottomCancelClick?: () => void | Promise<void>;
}

const SharedPageLayout: FC<Props> = ({
  title = '',
  cardPadding = PAGE_SECTION_PADDING,
  isNestSpinFlexContainer = false,
  centerTitle,
  removeSidebar = false,
  children,
  tip,
  rightTitle,
  contentWrapByCard = true,
  isHideHeader = false,
  isShowFixedBottomLayout = false,
  isNeedHelp = true,
  renderFixedBottomLayout,
  bottomOkText = i18n.t('confirm'),
  bottomCancelText = i18n.t('cancel'),
  bottomTip,
  bottomOkButtonIsLoading,
  bottomCancelButtonIsLoading,
  onBottomOkClick,
  onBottomCancelClick,
}) => {
  const appFlagValue = useRecoilValue(appFlag);
  const [appStateValue, setAppState] = useRecoilState(appState);
  const [okButtonIsLoading, setOkButtonIsLoading] = useState(false);
  const [cancelButtonIsLoading, setCancelButtonIsLoading] = useState(false);

  useEffect(() => {
    setAppState({
      ...appStateValue,
      hideSidebar: Boolean(removeSidebar),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [removeSidebar, setAppState]);

  return (
    <Container id="share-page-layout" isHideHeader={isHideHeader}>
      {!isHideHeader && (
        <PageHeader>
          <GridRow gap="10">
            <PageTitle className="title">{title}</PageTitle>
            {tip && (
              <Tip content={tip} position="rt">
                <QuestionCircle />
              </Tip>
            )}
            {centerTitle && <PageCenterTitle>{centerTitle}</PageCenterTitle>}
            <PageRightTitle>
              <Space size={12}>
                {isNeedHelp && (
                  <button
                    className="custom-text-button"
                    onClick={() => {
                      window.open(`${appFlagValue[FlagKey.HELP_DOC_URL]}`, '_blank');
                    }}
                  >
                    帮助文档
                  </button>
                )}
                {rightTitle}
              </Space>
            </PageRightTitle>
          </GridRow>
        </PageHeader>
      )}
      {contentWrapByCard ? (
        <PageSectionCard
          $cardPadding={cardPadding}
          $isNestSpinFlexContainer={isNestSpinFlexContainer}
          bordered={false}
        >
          {children}
        </PageSectionCard>
      ) : (
        children
      )}
      {isShowFixedBottomLayout && (
        <FixedBottomContainer>
          {renderFixedBottomLayout ? (
            renderFixedBottomLayout()
          ) : (
            <>
              <Button
                type="primary"
                onClick={onOkButtonClick}
                loading={bottomOkButtonIsLoading || okButtonIsLoading}
              >
                {bottomOkText}
              </Button>
              <Button
                onClick={onCancelButtonClick}
                loading={bottomCancelButtonIsLoading || cancelButtonIsLoading}
              >
                {bottomCancelText}
              </Button>
              {bottomTip && <TitleWithIcon isShowIcon={true} isLeftIcon={true} title={bottomTip} />}
            </>
          )}
        </FixedBottomContainer>
      )}
    </Container>
  );

  async function onOkButtonClick() {
    if (!onBottomOkClick) return;

    try {
      setOkButtonIsLoading(true);
      await onBottomOkClick();
      setOkButtonIsLoading(false);
    } catch (e) {
      setOkButtonIsLoading(false);
      Message.error(e.message);
    }
  }

  async function onCancelButtonClick() {
    if (!onBottomCancelClick) return;

    try {
      setCancelButtonIsLoading(true);
      await onBottomCancelClick();
      setCancelButtonIsLoading(false);
    } catch (e) {
      setCancelButtonIsLoading(false);
      Message.error(e.message);
    }
  }
};

export default SharedPageLayout;
