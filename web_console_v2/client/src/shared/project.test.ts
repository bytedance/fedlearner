import { wrapWithDomainName, unwrapDomainName, DOMAIN_PREFIX, DOMAIN_SUFFIX } from './project';

describe("Domain's wrap/unwrap", () => {
  it('Wrap should works fine', () => {
    expect(wrapWithDomainName('case1')).toBe(`${DOMAIN_PREFIX}case1${DOMAIN_SUFFIX}`);
  });

  it('Unwrap should works fine', () => {
    expect(unwrapDomainName('fl-case2.com')).toBe('case2');
  });
});
