export function isObject(target) {
  return target && typeof target === 'object';
}

export function deepMergeObject(source, target) {
  if (!isObject(target) || !isObject(source)) return source;
  const sourceKeys = Object.keys(source);
  const result = {};
  for (const key of sourceKeys) {
    const sourceValue = source[key];
    const targetValue = target[key];
    if (Array.isArray(sourceValue) && Array.isArray(targetValue)) {
      result[key] = targetValue.concat(sourceValue);
    } else if (isObject(sourceValue) && isObject(targetValue)) {
      result[key] = deepMergeObject(sourceValue, { ...targetValue });
    } else if (targetValue) {
      result[key] = targetValue;
    } else {
      result[key] = sourceValue;
    }
  }
  return result;
}
