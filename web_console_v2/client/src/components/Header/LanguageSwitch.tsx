import { FALLBACK_LNG, setLocale } from 'i18n';
import React, { FC, useState } from 'react';
import styled from 'styled-components';
import { FedLanguages } from 'typings/app';
import classNames from 'classnames';
import store from 'store2';
import LOCAL_STORAGE_KEYS from 'shared/localStorageKeys';
import { MixinCommonTransition } from 'styles/mixins';

const Container = styled.div`
  position: relative;
  display: flex;
  padding: 3px;
  border: 1px solid var(--gray3);
  border-radius: 100px;
`;
const Lng = styled.div`
  ${MixinCommonTransition()}
  position: relative;
  z-index: 2;
  width: 32px;
  line-height: 20px;
  height: 20px;
  text-align: center;
  font-size: 12px;
  cursor: pointer;

  &.is-active {
    font-weight: bold;
    color: white;
  }
`;

const Slider = styled.div`
  ${MixinCommonTransition()}
  position: absolute;
  z-index: 1;
  width: 32px;
  height: 20px;
  left: 3px;
  border-radius: 100px;
  background-color: var(--darkGray3);
`;

const Langs = [
  {
    val: FedLanguages.Chinese,
    label: '简',
  },
  {
    val: FedLanguages.English,
    label: 'En',
  },
];

const LanguageSwitch: FC = () => {
  const [current, setLng] = useState(store.get(LOCAL_STORAGE_KEYS.language || FALLBACK_LNG));
  const idx = Langs.findIndex((item) => item.val === current);
  const sliderOffset = idx * 32;

  return (
    <Container>
      {Langs.map((lng) => {
        return (
          <Lng
            key={lng.val}
            className={classNames({ 'is-active': current === lng.val })}
            onClick={onLngClick.bind(null, lng.val)}
          >
            {lng.label}
          </Lng>
        );
      })}
      <Slider style={{ transform: `translateX(${sliderOffset}px)` }} />
    </Container>
  );

  function onLngClick(val: FedLanguages) {
    setLocale(val);
    setLng(val);
  }
};

export default LanguageSwitch;
