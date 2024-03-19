import React, { FC, useState, useEffect, useCallback } from 'react';
import { Input, InputNumberProps } from '@arco-design/web-react';
import { convertCpuCoreToM, convertCpuMToCore } from 'shared/helpers';

/**
 * <input type="text"> 伪装成的 number input，实现了 ArcoDesign InputNumber 的部分功能：
 * * 不支持键盘上下箭头加减值
 * * 不支持 mode="button" 模式
 */
const IntegerTextInput: FC<InputNumberProps> = (props) => {
  const {
    min = 0,
    max = Number.MAX_SAFE_INTEGER,
    value,
    defaultValue,
    precision = 0,
    prefix,
    suffix,
    error,
    onChange,
    disabled,
  } = props;
  const isControlledMode = Object.prototype.hasOwnProperty.call(props, 'value');
  const [innerValue, setInnerValue] = useState<number | undefined>(
    getInitValue(value, defaultValue),
  );
  const [inputVal, setInputVal] = useState<string | undefined>(() => {
    return typeof innerValue === 'number' ? innerValue.toFixed(precision) : undefined;
  });
  const setInnerValueProxy = useCallback(
    (val: number | string | undefined) => {
      switch (typeof val) {
        case 'undefined':
          setInnerValue(undefined);
          setInputVal('');
          break;
        case 'number':
          setInnerValue(val);
          setInputVal(val.toFixed(precision));
          break;
        case 'string':
          const digital = parseFloat(val);
          if (isNaN(digital)) {
            return;
          }
          setInnerValue(digital);
          setInputVal(digital.toFixed(precision));
          break;
      }
    },
    [precision],
  );

  const setValue = (val: number) => {
    let outputVal = val;
    if (val > max) {
      outputVal = max;
    } else if (val < min) {
      outputVal = min;
    }

    if (outputVal === innerValue) {
      setInnerValueProxy(outputVal);
      return;
    }
    if (!isControlledMode) {
      setInnerValueProxy(outputVal);
    }

    onChange?.(outputVal);
  };
  const handleBlur = (evt: React.FocusEvent<HTMLInputElement>) => {
    const val = evt.target.value;
    const isFloat = precision > 0;
    const digitalVal = isFloat ? parseFloat(val) : parseInt(val);
    if (isNaN(digitalVal)) {
      setInnerValueProxy(innerValue);
      return;
    }

    if (isFloat) {
      const fixedNumber = digitalVal.toFixed(precision);
      setValue(parseFloat(fixedNumber));
      return;
    }
    setValue(digitalVal);
  };

  useEffect(() => {
    if (isControlledMode) {
      const digitalVal = value as number;
      setInnerValueProxy(digitalVal);
    }
  }, [value, isControlledMode, min, max, setInnerValueProxy]);

  return (
    <Input
      error={error}
      value={inputVal}
      onBlur={handleBlur}
      onChange={setInputVal}
      prefix={prefix}
      suffix={suffix}
      disabled={disabled}
    />
  );
};

function getInitValue(value?: string | number, defaultVal?: number): number | undefined {
  if (typeof value !== 'undefined') {
    const valueType = typeof value;
    if (valueType === 'string') {
      const digital = parseFloat(value as string);
      return isNaN(digital) ? undefined : digital;
    }
    if (valueType === 'number') {
      return value as number;
    }
  }

  return defaultVal;
}

type OnChangeWithSuffixProps = Omit<InputNumberProps, 'onChange'> & {
  onChange?: (val: string) => void;
};
export const OnChangeWithSuffix: FC<OnChangeWithSuffixProps> = ({ onChange, suffix, ...rest }) => {
  const onChangeWrapper = (val: number) => {
    onChange?.(`${val}${suffix || ''}`);
  };
  return <IntegerTextInput {...rest} suffix={suffix} onChange={onChangeWrapper} />;
};

export const CpuInput: FC<Omit<OnChangeWithSuffixProps, 'suffix'>> = ({
  onChange,
  value,
  ...props
}) => {
  const onChangeWrapper = (val: string) => {
    onChange?.(convertCpuCoreToM(val, true));
  };

  return (
    <OnChangeWithSuffix
      suffix="Core"
      precision={1}
      onChange={onChangeWrapper}
      value={value ? convertCpuMToCore(value as string, true) : undefined}
      {...props}
    />
  );
};
export const MemInput: FC<Omit<OnChangeWithSuffixProps, 'suffix'>> = ({ ...props }) => {
  return <OnChangeWithSuffix suffix="Gi" {...props} />;
};

export default IntegerTextInput;
