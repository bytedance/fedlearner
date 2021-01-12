export function isHead(target: any, source: any[]) {
  return source.indexOf(target) === 0;
}

export function isLast(target: any, source: any[]) {
  return source.lastIndexOf(target) === source.length - 1;
}
