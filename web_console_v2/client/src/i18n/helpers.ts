export type I18nMessage = { zh: string; en?: string | null }
export type I18nMessageModule = { [key: string]: I18nMessage }

export function separateLng(msgModule: I18nMessageModule) {
  const ret: { [key in 'zh' | 'en']: { [key: string]: string | null } } = {
    zh: {},
    en: {},
  }

  Object.entries(msgModule).forEach(([key, values]) => {
    ret.zh[key] = values.zh
    ret.en[key] = values.en || null
  })

  return ret
}
