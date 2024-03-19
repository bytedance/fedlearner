export function composeOtherJobRef(jobUuid: string, varUuid: string) {
  if (!jobUuid || !varUuid) return '';

  return `workflow.jobs['${jobUuid}'].variables.${varUuid}`;
}

/** @returns [job-uuid, var-uuid, extra-field-value] or [job-name, var-name, extra-field-name] */
export function parseOtherJobRef(reference?: string): [string, string, string] {
  if (!reference) return [undefined, undefined] as never;

  const fragments = reference.split(/\.|']\.?|\['/);

  if (fragments.length < 5) {
    return [undefined, undefined, undefined] as never;
  }

  const [, , job, , variable, extraField] = fragments;

  return [job, variable, extraField];
}

export function parseJobPropRef(reference?: string) {
  if (!reference) return [undefined, undefined] as never;

  if (reference.startsWith('self.')) {
    return ['__SELF__', reference.split(/\.|']\.?|\['/)[1]];
  }

  const fragments = reference.split(/\.|']\.?|\['/);

  const [, , job, prop] = fragments;

  return [job, prop];
}

export function composeJobPropRef(params: { isSelf: boolean; job?: string; prop?: string }) {
  const { isSelf, job, prop } = params;

  if (!prop) return undefined as never;

  if (isSelf) {
    return `self.${prop}`;
  }
  return `workflow.jobs['${job}'].${prop}`;
}

export function composSelfRef(varUuid?: string) {
  if (!varUuid) return undefined as never;

  return `self.variables.${varUuid}`;
}

export function parseSelfRef(val?: string) {
  // e.g. self.variables.${uuid}
  // If compoment type of variable is VariableComponent.AlgorithmSelect, self.variables.${uuid}.path or self.variables.${uuid}.path
  const list = val?.split('.') ?? [];
  return list[2] || (undefined as never);
}

export function composeWorkflowRef(varUuid?: string) {
  if (!varUuid) return undefined as never;

  return `workflow.variables.${varUuid}`;
}

export function parseWorkflowRef(val?: string) {
  // e.g. workflow.variables.${uuid}
  // If compoment type of variable is VariableComponent.AlgorithmSelect, workflow.variables.${uuid}.path or workflow.variables.${uuid}.path
  const list = val?.split('.') ?? [];
  return list[2] || (undefined as never);
}
