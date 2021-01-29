export const DOMAIN_PREFIX = 'fl-';
export const DOMAIN_SUFFIX = '.com';

/** Turn user input 'xxx' to 'fl-xxx.com' */
export function wrapWithDomainName(input: string) {
  return `${DOMAIN_PREFIX}${input}${DOMAIN_SUFFIX}`;
}
/** Remove prefix and suffix of 'fl-xxx.com'  */
export function unwrapDomainName(input: string) {
  return input.replace(DOMAIN_PREFIX, '').replace(DOMAIN_SUFFIX, '');
}
