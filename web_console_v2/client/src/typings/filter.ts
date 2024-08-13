export enum FilterOp {
  UNKNOWN = 'UNKNOWN', // 0
  EQUAL = 'EQUAL', // =
  IN = 'IN', // :
  CONTAIN = 'CONTAIN', // ~=
  GREATER_THAN = 'GREATER_THAN', // >
  LESS_THAN = 'LESS_THAN', // <
}

export enum FilterExpressionKind {
  BASIC = 'basic',
  AND = 'and',
  OR = 'or',
}

export interface SimpleExpression {
  field: string;
  op: FilterOp;
  bool_value?: boolean;
  string_value?: string;
  number_value?: number;
}

export interface FilterExpression {
  kind: FilterExpressionKind;
  simple_exp?: SimpleExpression;
  exps?: FilterExpression[];
}
