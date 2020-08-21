import React, { createContext, useContext, useReducer } from "react";
import produce from 'immer'

const state = {
  federationID: -1,
}

const actions = {
  setFederationID (state, id) {
    state.federationID = id
  }
}

const reducer = (state = state, action) =>
  produce(state, draft => {
    const act = actions[action['type']]
    act && act(draft, action['payload'])
  })

const StateContext = createContext();

export const StateProvider = ({ children }) => (
  <StateContext.Provider value={useReducer(reducer, state)}>
    {children}
  </StateContext.Provider>
);

export const useStateValue = () => {
  return useContext(StateContext)
};
