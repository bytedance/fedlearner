export const FLAppStatus = {
  Running: 'FLStateRunning',
  Failed: 'FLStateFailed',
  Complete: 'FLStateComplete',
  ShutDown: 'FLStateShutDown',
};

export const JobStatus = {
  Running: 'Running',
  Failed: 'Failed',
  Complete: 'Complete',
  ShutDown: 'ShutDown',
  Killed: 'Killed',
}

export function handleStatus(statusStr) {
  if (typeof statusStr !== 'string') return statusStr;
  return statusStr.replace('FLState', '');
}

export function getStatusColor(statusStr) {
  switch (statusStr) {
    case FLAppStatus.Running:
    case JobStatus.Running:
      return 'lightblue';
    case FLAppStatus.Failed:
    case JobStatus.Failed:
      return 'red';
    case FLAppStatus.Complete:
    case JobStatus.Complete:
      return 'limegreen';
    case FLAppStatus.ShutDown:
    case JobStatus.ShutDown:
      return 'brown';
    default:
      return undefined;
  }
}
