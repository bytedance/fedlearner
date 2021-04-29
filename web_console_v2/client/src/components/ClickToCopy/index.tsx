import React, { FC } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { copyToClipboard } from 'shared/helpers';
import { message } from 'antd';

const Container = styled.div`
  cursor: pointer;
`;

type Props = {
  text: string;
};

const ClickToCopy: FC<Props> = ({ children, text }) => {
  const { t } = useTranslation();

  return <Container onClick={onClick}>{children}</Container>;

  function onClick() {
    const isOK = copyToClipboard(text);

    if (isOK) {
      message.success(t('app.copy_success'));
    }
  }
};

export default ClickToCopy;
