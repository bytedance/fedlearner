import React from 'react';
import { Checkbox } from '@arco-design/web-react';
import creditsIcon from 'assets/icons/credits-icon.svg';
import { useGetAppFlagValue } from 'hooks';
import { FlagKey } from 'typings/flag';
import './index.less';

type TPublishChecker = {
  value?: boolean;
  onChange?: (val: boolean) => void;
};

export default function PublishChecker(prop: TPublishChecker) {
  const { value, onChange } = prop;
  const handleOnChange = (val: boolean) => {
    onChange?.(val);
  };
  const bcs_support_enabled = useGetAppFlagValue(FlagKey.BCS_SUPPORT_ENABLED);
  return (
    <div className="publish-checker-container">
      <Checkbox checked={value} onChange={handleOnChange} />
      <div className="publish-text">
        <span>发布至工作区</span>
        <span>发布后，工作区中合作伙伴可使用该数据集</span>
      </div>
      {!!bcs_support_enabled && (
        <div className="credit-card">
          <img className="credit-icon" src={creditsIcon} alt="credit-icon" />
          100积分
        </div>
      )}
    </div>
  );
}
