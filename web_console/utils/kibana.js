const dayjs = require('dayjs');
const getConfig = require('./get_confg');

const JOB_METRICS = {
  data_join: [],
  psi_data_join: [],
  tree_model: [],
  nn_model: [
    {
      query: 'name%20:%22auc%22',
      mode: 'avg',
      title: 'auc',
    },
    {
      query: 'name%20:%22loss%22',
      mode: 'avg',
      title: 'loss',
    },
    {
      query: 'name%20:%22receive_timer%22',
      mode: 'avg',
      title: 'receive spend',
    },
    {
      query: 'name%20:%22iter_spend%22',
      mode: 'avg',
      title: 'per session run spend',
    },
    {
      query: 'name%20:%22resend_counter%22',
      mode: 'sum',
      title: 'count of resend',
    },
    {
      query: 'name%20:%22send_counter%22',
      mode: 'sum',
      title: 'count of send',
    },
    {
      query: 'name%20:%22reconnect_counter%22',
      mode: 'sum',
      title: 'count of reconnect',
    },
    {
      query: 'name%20:%22load_data_block_counter%22',
      mode: 'sum',
      title: 'count of load data block',
    },
    {
      query: 'name%20:%22load_data_block_fail_counter%22',
      mode: 'sum',
      title: 'count of fail to load data block',
    },
  ],
};

const config = getConfig({
  KIBANA_HOST: process.env.NEXT_PUBLIC_KIBANA_HOST,
  KIBANA_PORT: process.env.NEXT_PUBLIC_KIBANA_PORT,
});

function getBaseUrl(application_id, from, to) {
  return `https://${config.KIBANA_HOST}:${config.KIBANA_PORT}/fedlearner/app/kibana#/visualize/edit/95e50f80-dd3a-11ea-a472-39251c5aaace?_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:'${from}',to:'${to}'))&_a=(filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'73340100-dd33-11ea-a472-39251c5aaace',key:tags.application_id,negate:!f,params:(query:${application_id}),type:phrase),query:(match_phrase:(tags.application_id:${application_id})))),linked:!f,`;
}

/**
 * used for job creation at server-side
 *
 * @param {string} application_id - name of Kubernetes application
 * @param {string} from - date string in ISO format
 * @param {string} to - date string in ISO format
 * @param {string} query - metrics target
 * @param {string} mode - computing function of ElasticSearch
 * @param {string} title - metrics title
 * @return {string} - a Kibana dashboard url
 */
function getDashboardUrl(application_id, from, to, query, mode, title) {
  const baseUrl = getBaseUrl(application_id, from, to);
  return `${baseUrl}query:(language:kuery,query:'${query}'),uiState:(),vis:(aggs:!((enabled:!t,id:'1',params:(field:value),schema:metric,type:${mode}),(enabled:!t,id:'2',params:(drop_partials:!f,extended_bounds:(),field:date_time,interval:auto,min_doc_count:1,scaleMetricValues:!f,timeRange:(from:'${from}',to:'${to}'),useNormalizedEsInterval:!t),schema:segment,type:date_histogram),(enabled:!t,id:'3',params:(field:name.keyword,missingBucket:!f,missingBucketLabel:Missing,order:desc,orderBy:'1',otherBucket:!f,otherBucketLabel:Other,size:5),schema:group,type:terms)),params:(addLegend:!t,addTimeMarker:!f,addTooltip:!t,categoryAxes:!((id:CategoryAxis-1,labels:(filter:!t,show:!t,truncate:100),position:bottom,scale:(type:linear),show:!t,style:(),title:(),type:category)),dimensions:(series:!((accessor:1,aggType:terms,format:(id:terms,params:(id:string,missingBucketLabel:Missing,otherBucketLabel:Other,parsedUrl:(basePath:%2Ffedlearner,origin:'https:%2F%2F${config.KIBANA_HOST}',pathname:%2Ffedlearner%2Fapp%2Fkibana))),label:'name.keyword:%20Descending',params:())),x:(accessor:0,aggType:date_histogram,format:(id:date,params:(pattern:'HH:mm:ss')),label:'date_time%20per%20second',params:(bounds:(max:'${to}',min:'${from}'),date:!t,format:'HH:mm:ss',interval:PT1S,intervalESUnit:s,intervalESValue:1)),y:!((accessor:2,aggType:avg,format:(id:number,params:(parsedUrl:(basePath:%2Ffedlearner,origin:'https:%2F%2F${config.KIBANA_HOST}',pathname:%2Ffedlearner%2Fapp%2Fkibana))),label:'Average%20value',params:()))),grid:(categoryLines:!f),labels:(),legendPosition:right,seriesParams:!((data:(id:'1',label:'${mode}%20of%20value'),drawLinesBetweenPoints:!t,interpolate:linear,lineWidth:2,mode:normal,show:!t,showCircles:!t,type:line,valueAxis:ValueAxis-1)),thresholdLine:(color:%23E7664C,show:!f,style:full,value:10,width:1),times:!(),type:line,valueAxes:!((id:ValueAxis-1,labels:(filter:!f,rotate:0,show:!t,truncate:100),name:LeftAxis-1,position:left,scale:(mode:normal,type:linear),show:!t,style:(),title:(text:'${mode}%20of%20value'),type:value))),title:${title},type:line))`;
}

/**
 * get Kibana dashboard urls of a job
 *
 * @param {Object} job - a job instance
 * @return {string[]} - a list of Kibana dashboard url
 */
function getJobDashboardUrls(job) {
  const { name, job_type, created_at } = job;
  const from = dayjs(created_at).toISOString();
  const to = dayjs().toISOString();
  return JOB_METRICS[job_type].map(({ query, mode, title }) => getDashboardUrl(name, from, to, query, mode, title));
}

module.exports = getJobDashboardUrls;
