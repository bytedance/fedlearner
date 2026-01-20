import {
  constructExpressionTree,
  serializeFilterExpression,
  confirmValue,
  operationMap,
  expression2Filter,
} from './filter';
import { FilterExpressionKind, FilterOp } from '../typings/filter';

describe('expression serialization', () => {
  it('cnstruct expression tree', () => {
    const nodes = [
      {
        field: 'state',
        op: FilterOp.EQUAL,
        string_value: 'RUNNING',
      },
      {
        field: 'favour',
        op: FilterOp.EQUAL,
        bool_value: true,
      },
    ];
    constructExpressionTree(nodes);
  });

  it('serialization', () => {
    const expression = {
      kind: FilterExpressionKind.AND,
      exps: [
        {
          kind: FilterExpressionKind.BASIC,
          simple_exp: {
            field: 'state',
            op: FilterOp.EQUAL,
            string_value: 'RUNNING',
          },
        },
        {
          kind: FilterExpressionKind.BASIC,
          simple_exp: {
            field: 'favour',
            op: FilterOp.EQUAL,
            bool_value: true,
          },
        },
        {
          kind: FilterExpressionKind.AND,
          exps: [
            {
              kind: FilterExpressionKind.BASIC,
              simple_exp: {
                field: 'state',
                op: FilterOp.EQUAL,
                string_value: 'RUNNING',
              },
            },
            {
              kind: FilterExpressionKind.BASIC,
              simple_exp: {
                field: 'count',
                op: FilterOp.EQUAL,
                num_value: 10,
              },
            },
          ],
        },
      ],
    };
    serializeFilterExpression(expression);
  });

  const expressionList = [
    {
      kind: FilterExpressionKind.BASIC,
      simple_exp: {
        field: 'state',
        op: FilterOp.EQUAL,
        string_value: 'RUNNING',
      },
    },
    {
      kind: FilterExpressionKind.BASIC,
      simple_exp: {
        field: 'count',
        op: FilterOp.EQUAL,
        num_value: 10,
      },
    },
    {
      kind: FilterExpressionKind.BASIC,
      simple_exp: {
        field: 'favour',
        op: FilterOp.EQUAL,
        bool_value: true,
      },
    },
  ];

  it('confim value', () => {
    expressionList.forEach((item) => {
      return confirmValue(item.simple_exp);
    });
  });

  it('operationMap', () => {
    expressionList.forEach((item) => {
      return operationMap(item.simple_exp.op);
    });
  });

  it('expression2Filter', () => {
    const expression = '(and((state=["SUCCESS","FAILED"])(is_publish=true))';
    expression2Filter(expression);
  });
});
