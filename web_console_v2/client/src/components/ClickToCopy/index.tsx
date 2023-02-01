/* istanbul ignore file */

import React, { FC } from 'react';
import i18n from 'i18n';

import { newCopyToClipboard, to } from 'shared/helpers';
import { Message } from '@arco-design/web-react';

type Props = {
  /** Text that will be copied  */
  text: string;
  /** Tip that it will show when copied success */
  successTip?: string;
  /** Tip that it will show when copied fail */
  failTip?: string;
};

const ClickToCopy: FC<Props> = ({
  children,
  text,
  successTip = i18n.t('app.copy_success'),
  failTip = i18n.t('app.copy_fail'),
}) => {
  return (
    <div
      style={{
        cursor: 'pointer',
      }}
      onClick={onClick}
    >
      {children}
    </div>
  );

  async function onClick() {
    const [, error] = await to(newCopyToClipboard(text));
    if (error) {
      return Message.error(failTip!);
    }
    return Message.success(successTip!);
  }
};

export default ClickToCopy;
