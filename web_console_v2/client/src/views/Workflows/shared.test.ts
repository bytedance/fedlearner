import { hydrate } from './shared';

import { Variable } from 'typings/variable';

import {
  nameInput,
  codeEditor,
  featureSelect,
  envsInput,
  forceObjectInput,
  forceListInput,
} from 'services/mocks/v2/variables/examples';

describe('hydrate', () => {
  const testVariables: Variable[] = [
    nameInput,
    codeEditor,
    featureSelect,
    envsInput,
    forceObjectInput,
    forceListInput,
  ];
  it('normal', () => {
    const testVariablesAllWithNewValue: Variable[] = [
      { ...nameInput, value: 'new value' },
      { ...codeEditor, value: { 'main.js': 'var a = 2;' } },
      { ...featureSelect, value: { a: 2 } },
      {
        ...envsInput,
        value: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
      },
      { ...forceObjectInput, value: { a: 2 } },
      { ...forceListInput, value: [{ a: 2 }] },
    ];

    const testVariablesSomeWithNewValue: Variable[] = [
      nameInput,
      codeEditor,
      { ...featureSelect, value: { a: 2 } },
      {
        ...envsInput,
        value: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
      },
      { ...forceObjectInput, value: { a: 2 } },
      { ...forceListInput, value: [{ a: 2 }] },
    ];

    expect(hydrate(testVariables, undefined)).toEqual([]);
    expect(hydrate(testVariables, {})).toEqual(testVariables);
    expect(
      hydrate(testVariables, {
        [nameInput.name]: 'new value',
        [codeEditor.name]: { 'main.js': 'var a = 2;' },
        [featureSelect.name]: { a: 2 },
        [envsInput.name]: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
        [forceObjectInput.name]: { a: 2 },
        [forceListInput.name]: [{ a: 2 }],
      }),
    ).toEqual(testVariablesAllWithNewValue);
    expect(
      hydrate(testVariables, {
        [featureSelect.name]: { a: 2 },
        [envsInput.name]: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
        [forceObjectInput.name]: { a: 2 },
        [forceListInput.name]: [{ a: 2 }],
      }),
    ).toEqual(testVariablesSomeWithNewValue);
  });
  it('isStringifyVariableValue', () => {
    expect(testVariables.every((item) => typeof item.value === 'string')).toBeFalsy();
    const finalVariables = hydrate(
      testVariables,
      {
        [featureSelect.name]: { a: 2 },
        [envsInput.name]: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
        [forceObjectInput.name]: { a: 2 },
        [forceListInput.name]: [{ a: 2 }],
      },
      {
        isStringifyVariableValue: true,
      },
    );
    expect(finalVariables.every((item) => typeof item.value === 'string')).toBeTruthy();
  });
  it('isProcessVariableTypedValue', () => {
    const finalVariables = hydrate(
      testVariables,
      {
        [nameInput.name]: 'namename',
        [featureSelect.name]: { a: 2 },
        [envsInput.name]: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
        [forceObjectInput.name]: { a: 2 },
        [forceListInput.name]: [{ a: 2 }],
      },
      {
        isProcessVariableTypedValue: true,
      },
    );

    expect(finalVariables).toEqual([
      { ...nameInput, typed_value: 'namename', value: 'namename' },
      codeEditor,
      { ...featureSelect, typed_value: { a: 2 }, value: { a: 2 } },
      {
        ...envsInput,
        typed_value: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
        value: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
      },
      { ...forceObjectInput, typed_value: { a: 2 }, value: { a: 2 } },
      { ...forceListInput, typed_value: [{ a: 2 }], value: [{ a: 2 }] },
    ]);
  });
  it('isStringifyVariableWidgetSchema', () => {
    expect(testVariables.every((item) => typeof item.widget_schema === 'string')).toBeFalsy();
    const finalVariables = hydrate(
      testVariables,
      {
        [featureSelect.name]: { a: 2 },
        [envsInput.name]: [
          { name: 'nn1', value: 'nv1' },
          { name: 'nn2', value: 'nv2' },
        ],
        [forceObjectInput.name]: { a: 2 },
        [forceListInput.name]: [{ a: 2 }],
      },
      {
        isStringifyVariableWidgetSchema: true,
      },
    );
    expect(finalVariables.every((item) => typeof item.widget_schema === 'string')).toBeTruthy();
  });
});
