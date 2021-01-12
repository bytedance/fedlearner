import React, { ReactElement } from 'react';
import styled from 'styled-components';
import { ReactComponent as AddSvg } from 'assets/images/add.svg';
import { useTranslation } from 'react-i18next';

const Container = styled.div`
  display: flex;
  flex-direction: column;
`;

const AddSvgWrapper = styled.div`
  margin-top: 28px;
  display: block;
`;

const TipWrapper = styled.div`
  font-weight: 500;
  font-size: 14px;
  line-height: 24px;
  color: var(--gray8);
  margin: 28px 4px 0px;
`;

const SuffixWrapper = styled.div`
  font-size: 12px;
  line-height: 18px;
  text-align: center;
  color: var(--gray6);
  margin: 0px 4px;
  height: 40px;
`;

interface Props {
  suffix?: string;
}

function UploadArea({ suffix }: Props): ReactElement {
  const { t } = useTranslation();
  return (
    <Container>
      <AddSvgWrapper>
        <AddSvg />
      </AddSvgWrapper>
      <TipWrapper>{t('project.drag_to_upload')}</TipWrapper>
      <SuffixWrapper>{suffix}</SuffixWrapper>
    </Container>
  );
}

export default UploadArea;
