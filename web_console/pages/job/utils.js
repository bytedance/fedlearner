export const FLAppStatus = {
  Running: 'FLStateRunning',
  Failed: 'FLStateFailed',
  Complete: 'FLStateComplete',
  ShutDown: 'FLStateShutDown',
};

export function handleStatus(statusStr) {
  return statusStr.replace('FLState', '');
}

export function getStatusColor(statusStr) {
  switch (statusStr) {
    case FLAppStatus.Running:
      return 'lightblue';
    case FLAppStatus.Failed:
      return 'red';
    case FLAppStatus.Complete:
      return 'limegreen';
    case FLAppStatus.ShutDown:
      return 'brown';
    default:
      return undefined;
  }
}
