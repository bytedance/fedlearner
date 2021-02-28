import { groupByDependencies, convertToChartElements, getNodeIdByJob } from './helpers';
import { normalTemplate } from 'services/mocks/v2/workflow_templates/examples';
import { NodeDataRaw } from './types';

describe('Convert job definitions to chart elements', () => {
  const jobs = normalTemplate.config?.job_definitions as NodeDataRaw[];
  const convertParams = { jobs };
  const convertOptions = { type: 'config', selectable: false } as any;

  const converted = convertToChartElements(convertParams, convertOptions);

  it('Should works without global variables', () => {
    // The normalTemplate shoudl convert to:
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

  it('Should works without global variables', () => {
    expect(converted.filter((node) => node.type === 'config').length).toBe(
      normalTemplate.config!.job_definitions!.length,
    );
  });

  it('getNodeIdByJob', () => {
    expect(getNodeIdByJob(jobs[0])).toBe(converted[0].id);
  });
});
