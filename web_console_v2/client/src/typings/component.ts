export type ComponentSize = 'small' | 'medium' | 'large' | 'default';

export interface StyledComponetProps {
  className?: string;
  [key: string]: any;
}
export interface PaginationConfig {
  total: number;
  page_size: number;
  page: number;
}

export enum DisplayType {
  Card = 1,
  Table = 2,
}
