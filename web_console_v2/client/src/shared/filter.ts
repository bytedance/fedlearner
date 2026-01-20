import {
  FilterExpression,
  FilterExpressionKind,
  FilterOp,
  SimpleExpression,
} from '../typings/filter';

export let serializedExpression = '';

export function constructExpressionTree(simpleNodes: SimpleExpression[]) {
  if (simpleNodes.length === 0) return;
  const exporessioNodes = simpleNodes.map((item) => {
    return {
      kind: FilterExpressionKind.BASIC,
      simple_exp: item,
    };
  });
  if (simpleNodes.length === 1) {
    return serializeFilterExpression(exporessioNodes[0]);
  }
  const expressionTree = {
    kind: FilterExpressionKind.AND,
    exps: exporessioNodes,
  };

  return serializeFilterExpression(expressionTree);
}

/**
 * preorder traversal to build serialized expressions
 * @param expression
 */
export function serializeFilterExpression(expression: FilterExpression) {
  expressionSerialize(expression);
  // clear serializedExpression
  const tempSerializedExpression = serializedExpression;
  serializedExpression = '';
  return tempSerializedExpression;
}

export function expressionSerialize(expression: FilterExpression) {
  if (expression.kind === FilterExpressionKind.BASIC) {
    serializedExpression += `(${expression.simple_exp?.field}${operationMap(
      expression.simple_exp?.op!,
    )}${confirmValue(expression.simple_exp!)})`;
    return;
  }
  if (expression.kind === FilterExpressionKind.AND || expression.kind === FilterExpressionKind.OR) {
    serializedExpression += `(${expression.kind}`;
    expression.exps?.forEach((item, index) => {
      expressionSerialize(item);
      if (expression.exps && expression.exps.length - 1 === index) {
        serializedExpression += ')';
      }
    });
  }
}

export function confirmValue(simpleExp: SimpleExpression) {
  if (simpleExp.string_value !== undefined) {
    return `"${simpleExp.string_value}"`;
  }
  if (simpleExp.number_value !== undefined) {
    return simpleExp.number_value;
  }
  if (simpleExp.bool_value !== undefined) {
    return simpleExp.bool_value;
  }
  return;
}

export function operationMap(op: string) {
  const map = new Map<string, string>();
  map.set(FilterOp.EQUAL, '=');
  map.set(FilterOp.IN, ':');
  map.set(FilterOp.CONTAIN, '~=');
  map.set(FilterOp.GREATER_THAN, '>');
  map.set(FilterOp.LESS_THAN, '<');

  return map.get(op);
}

/**
 * expression string -> filter object eg:
 * (and(state=["SUCCESS","FAILED"])(is_publish=true)) -->
 * {
 *   state: ["SUCCESS","FAILED"],
 *   is_publish: true,
 * }
 * @param expressionString
 */
export function expression2Filter(expressionString: string) {
  const res: { [key: string]: any } = {};
  if (!expressionString || !expressionString.length) {
    return res;
  }
  const pureFilterExpression = expressionString.startsWith('(and')
    ? expressionString.substring(4, expressionString.length - 1)
    : expressionString.substring(0, expressionString.length);
  const filterRegex = /(?<=\()(.+?)(?=\))/g;
  const operationRegex = /(:|=|~=|>|<)/;
  const valRegex = /("\[")/;
  const filterPairArray = pureFilterExpression.match(filterRegex);
  if (Array.isArray(filterPairArray)) {
    filterPairArray.forEach((pair) => {
      const index = pair.search(operationRegex);
      const [filterKey, filterVal] = [
        pair.substring(0, index).trim(),
        pair.indexOf('~=') === -1
          ? pair.substring(index + 1).trim()
          : pair.substring(index + 2).trim(),
      ];
      // "["SUCCESS", "PENDING"]" needs to delete " "
      res[filterKey] = valRegex.test(filterVal)
        ? JSON.parse(filterVal.slice(1, filterVal.length - 1))
        : JSON.parse(filterVal);
    });
  }
  return res;
}
