import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import cn from './resources/zh_CN'
import en from './resources/en'
import { FedLanguages } from 'typings/enum'

i18n.use(initReactI18next).init({
  resources: {
    cn,
    en,
  },
  lng: 'cn', // doesn't support hyphen eg. zh-cn
  keySeparator: false,
  interpolation: {
    escapeValue: false,
  },
})

export default i18n

export function setLocale(lng: FedLanguages) {
  i18n.changeLanguage(lng)
}
