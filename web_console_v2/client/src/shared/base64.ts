export function decodeBase64(str: string) {
  let temp = '';
  try {
    temp = decodeURIComponent(atob(str));
  } catch (e) {
    // the base 64 was invalid, then check for 'e.code === 5'.
    // (because 'DOMException.INVALID_CHARACTER_ERR === 5')
    if (e.code === 5) return str;
  }
  return temp;
}
