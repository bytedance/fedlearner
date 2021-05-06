export enum KibanaChartType {
  Rate = 'Rate',
  Ratio = 'Ratio',
  Numeric = 'Numeric',
  Time = 'Time',
  Timer = 'Timer',
}

export enum KibanaAggregator {
  Average = 'Average',
  Sum = 'Sum',
  Max = 'Max',
  Min = 'Min',
  Variance = 'Variance',
  // Aggregators below not works for Timer type chart
  StdDeviation = 'Std.Deviation',
  SumOfSquares = 'Sum of Squares',
}

export enum KibanaQueryFields {
  type = 'type',
  interval = 'interval',
  x_axis_field = 'x_axis_field',
  query = 'query',
  start_time = 'start_time',
  end_time = 'end_time',
  numerator = 'numerator',
  denominator = 'denominator',
  aggregator = 'aggregator',
  value_field = 'value_field',
  timer_names = 'timer_names',
  split = 'split',
}

export type KibanaQueryParams = Partial<Record<KibanaQueryFields, any>>;
