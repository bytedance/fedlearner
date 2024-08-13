import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import zh from './resources/zh_CN';
import en from './resources/en';
import { FedLanguages } from 'typings/app';
import store from 'store2';
import dayjs from 'dayjs';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';

export const FALLBACK_LNG = FedLanguages.Chinese;

const storedLng = store.get(LOCAL_STORAGE_KEYS.language);

const preferredLng = storedLng || FALLBACK_LNG;

store.set(LOCAL_STORAGE_KEYS.language, preferredLng);

dayjs.locale(preferredLng);

i18next.use(initReactI18next).init({
  resources: {
    zh,
    en,
  },
  fallbackLng: FedLanguages.Chinese,
  lng: preferredLng || FedLanguages.Chinese, // doesn't support hyphen eg. zh-cn
  keySeparator: '.',
  interpolation: {
    escapeValue: false,
  },
});

export default i18next;

export function setLocale(lng: FedLanguages) {
  i18next.changeLanguage(lng);
  dayjs.locale(lng);
}
