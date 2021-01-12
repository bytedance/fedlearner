import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import cn from './resources/zh_CN';
import en from './resources/en';
import { FedLanguages } from 'typings/app';
import store from 'store2';

const preferredLng = store.get('language');

i18n.use(initReactI18next).init({
  resources: {
    cn,
    en,
  },
  fallbackLng: FedLanguages.Chinese,
  lng: preferredLng || FedLanguages.Chinese, // doesn't support hyphen eg. zh-cn
  keySeparator: '.',
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;

export function setLocale(lng: FedLanguages) {
  i18n.changeLanguage(lng);
}
