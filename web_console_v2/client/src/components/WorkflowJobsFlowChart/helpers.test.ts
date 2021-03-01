import { groupByDependencies, convertToChartElements, getNodeIdByJob } from './helpers';
import { normalTemplate } from 'services/mocks/v2/workflow_templates/examples';
import { NodeDataRaw } from './types';
import { Variable } from 'typings/variable';

describe('Convert job definitions to chart elements', () => {
  const jobs = normalTemplate.config?.job_definitions as NodeDataRaw[];
  const convertParams = { jobs };
  const convertOptions = { type: 'config', selectable: false } as any;

  it('Group jobs into rows by deps should works fine(wiout global vars)', () => {
    // The normalTemplate should convert to:
    //
    // row-1        █1█
    //          ╭┈┈┈ ↓ ┈┈┈╮
    // row-2   █2█  █3█  █4█
    //          ╰┈┈┈ ↓ ┈┈┈╯
    // row-3        █5█
    //               ↓
    // row-4        █6█
    //
    const rows = groupByDependencies(convertParams, convertOptions);

    expect(rows.length).toBe(4);
    expect(rows[0].length).toBe(1);
    expect(rows[1].length).toBe(3);
    expect(rows[3].length).toBe(1);
    expect(rows[1][1].id).toBe(convertParams.jobs[2].name);
  });

  it('Group jobs into rows with global variables', () => {
    // The normalTemplate should convert to:
    //               ⦿ → Global config node
    // row-1        █1█
    //          ╭┈┈┈ ↓ ┈┈┈╮
    // row-2   █2█  █3█  █4█
    //          ╰┈┈┈ ↓ ┈┈┈╯
    // row-3        █5█
    //               ↓
    // row-4        █6█
    //
    const rows = groupByDependencies(
      { ...convertParams, globalVariables: normalTemplate.config?.variables as Variable[] },
      convertOptions,
    );

    expect(rows.length).toBe(5);
    expect(rows[0][0].type === 'global').toBeTruthy();
  });

  it('Should works without global variables', () => {
    const converted = convertToChartElements(convertParams, convertOptions);
    expect(converted.filter((node) => node.type === 'config').length).toBe(
      normalTemplate.config!.job_definitions!.length,
    );
  });

  it('getNodeIdByJob', () => {
    const converted = convertToChartElements(convertParams, convertOptions);
    expect(getNodeIdByJob(jobs[0])).toBe(converted[0].id);
  });
});
