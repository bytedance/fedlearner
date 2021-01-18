/* eslint-disable react-hooks/rules-of-hooks */
import React, { HTMLAttributes, ReactElement, createContext, useContext, useMemo } from 'react';

// 包裹前的图标属性
export interface ISvgIconProps {
  // 当前图标的唯一Id
  id: string;

  // 图标尺寸大小，默认1em
  size: number | string;
}

// 图标配置属性
export interface IIconConfig {
  // 图标尺寸大小，默认1em
  size: number | string;

  // CSS前缀
  prefix: string;

  // RTL是否开启
  rtl: boolean;
}

// 图标基础属性
export interface IIconBase {
  // 图标尺寸大小，默认1em
  size?: number | string;
}

// 安全的类型合并
export type Intersection<T, K> = T & Omit<K, keyof T>;

// 包裹后的图标非扩展属性
export interface IIcon extends IIconBase {
  spin?: boolean;
}

// 包裹后的图标属性
export type IIconProps = Intersection<IIcon, HTMLAttributes<HTMLSpanElement>>;

// 包裹前的图标
export type IconRender = (props: ISvgIconProps) => ReactElement;

// 包裹后的图标
export type Icon = (props: IIconProps) => ReactElement;

// 默认属性
export const DEFAULT_ICON_CONFIGS: IIconConfig = {
  size: '1em',
  rtl: false,
  prefix: 'sit-icon',
};

function guid(): string {
  return 'icon-' + (((1 + Math.random()) * 0x100000000) | 0).toString(16).substring(1);
}

// 属性转换函数
export function IconConverter(id: string, icon: IIconBase, config: IIconConfig): ISvgIconProps {
  return {
    size: icon.size || config.size,
    id,
  };
}

// 图标配置Context
const IconContext = createContext(DEFAULT_ICON_CONFIGS);

// 图标配置Provider
export const IconProvider = IconContext.Provider;

// 图标Wrapper
export function IconWrapper(name: string, rtl: boolean, render: IconRender, cssRender?: any): Icon {
  return (props: IIconProps) => {
    const { size, className, spin, ...extra } = props;

    const config = useContext(IconContext);

    const id = useMemo(guid, []);

    const svgProps = IconConverter(
      id,
      {
        size,
      },
      config,
    );

    const cls: string[] = ['anticon'];

    cls.push('anticon' + '-' + name);

    if (rtl && config.rtl) {
      cls.push('anticon-rtl');
    }

    if (spin) {
      cls.push('anticon-spin');
    }

    if (className) {
      cls.push(className);
    }

    return (
      <span {...extra} className={cls.join(' ')}>
        {render(svgProps)}
      </span>
    );
  };
}
