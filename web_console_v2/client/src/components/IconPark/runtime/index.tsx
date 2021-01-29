/* eslint-disable react-hooks/rules-of-hooks */
import React, { HTMLAttributes, ReactElement, createContext, useContext, useMemo } from 'react';

export interface ISvgIconProps {
  id: string;

  // defaults to 1em
  size: number | string;
}

export interface IIconConfig {
  // defaults to 1em
  size: number | string;

  // CSS prefix
  prefix: string;

  rtl: boolean;
}

export interface IIconBase {
  // defaults to 1em
  size?: number | string;
}

export type Intersection<T, K> = T & Omit<K, keyof T>;

export interface IIcon extends IIconBase {
  spin?: boolean;
}

export type IIconProps = Intersection<IIcon, HTMLAttributes<HTMLSpanElement>>;

export type IconRender = (props: ISvgIconProps) => ReactElement;

export type Icon = (props: IIconProps) => ReactElement;

export const DEFAULT_ICON_CONFIGS: IIconConfig = {
  size: '1em',
  rtl: false,
  prefix: 'ant-icon',
};

function guid(): string {
  return 'icon-' + (((1 + Math.random()) * 0x100000000) | 0).toString(16).substring(1);
}

export function IconConverter(id: string, icon: IIconBase, config: IIconConfig): ISvgIconProps {
  return {
    size: icon.size || config.size,
    id,
  };
}

const IconContext = createContext(DEFAULT_ICON_CONFIGS);

export const IconProvider = IconContext.Provider;

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
