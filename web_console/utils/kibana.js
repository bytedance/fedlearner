function getCommonUrl(start_time, end_time, application_id){
    let url = "http://ad-kibana.bytedance.net/fedlearner/app/kibana#" +
    "/visualize/edit/95e50f80-dd3a-11ea-a472-39251c5aaace?_g=(filter" +
    "s:!(),refreshInterval:(pause:!t,value:0),time:(from:'" + start_time +
    "',to:'" + end_time + "'))&_a=(filters:!(('$state':(store:appState)," +
    "meta:(alias:!n,disabled:!f,index:'73340100-dd33-11ea-a472-39251c" +
    "5aaace',key:tags.application_id,negate:!f,params:(query:" +
    application_id +"),type:phrase),query:(match_phrase:(tags.applica" +
    "tion_id:" + application_id + ")))),linked:!f,";
    return url;
}

/**
 * used for job creation at server-side
 *
 * @param {Object} start_time - Data's start time like "2020-08-19T09:42:04.402Z"
 * @param {Object} end_time - Data's end time like "2020-08-19T09:42:40.368Z"
 * @param {Object} application_id - Job's application id
 * @param {Object} query - Query method
 * @param {Object} mode - Data integration method
 * @param {Object} title - The title of chart
 * @return {Object} - A chart url
 */
function converted2Url(start_time, end_time, application_id, query, mode, title) {
    let url = getCommonUrl(start_time, end_time, application_id);
    url = url + "query:(language:kuery,query:'" + query +
        "'),uiState:(),vis:(aggs:!((enabled:!t,id:'1',params:(field:value)" +
        ",schema:metric,type:" + mode + "),(enabled:!t,id:'2',params:" +
        "(drop_partials:!f,extended_bounds:(),field:date_time,interval" +
        ":auto,min_doc_count:1,scaleMetricValues:!f,timeRange:(from:'" +
        start_time + "',to:'" + end_time + "'),useNormalizedEsInterval:" +
        "!t),schema:segment,type:date_histogram),(enabled:!t,id:'3'," +
        "params:(field:name.keyword,missingBucket:!f,missingBucketLa" +
        "bel:Missing,order:desc,orderBy:'1',otherBucket:!f,otherBuck" +
        "etLabel:Other,size:5),schema:group,type:terms)),params:(add" +
        "Legend:!t,addTimeMarker:!f,addTooltip:!t,categoryAxes:!((id" +
        ":CategoryAxis-1,labels:(filter:!t,show:!t,truncate:100),pos" +
        "ition:bottom,scale:(type:linear),show:!t,style:(),title:()," +
        "type:category)),dimensions:(series:!((accessor:1,aggType:te" +
        "rms,format:(id:terms,params:(id:string,missingBucketLabel:M" +
        "issing,otherBucketLabel:Other,parsedUrl:(basePath:%2Ffedlea" +
        "rner,origin:'http:%2F%2Fad-kibana.bytedance.net',pathname:%" +
        "2Ffedlearner%2Fapp%2Fkibana))),label:'name.keyword:%20Desce" +
        "nding',params:())),x:(accessor:0,aggType:date_histogram,for" +
        "mat:(id:date,params:(pattern:'HH:mm:ss')),label:'date_time%" +
        "20per%20second',params:(bounds:(max:'" + start_time + "',min:'" +
        end_time + "'),date:!t,format:'HH:mm:ss',interval:PT1S,interv" +
        "alESUnit:s,intervalESValue:1)),y:!((accessor:2,aggType:avg," +
        "format:(id:number,params:(parsedUrl:(basePath:%2Ffedlearner" +
        ",origin:'http:%2F%2Fad-kibana.bytedance.net',pathname:%2Ffe" +
        "dlearner%2Fapp%2Fkibana))),label:'Average%20value',params:(" +
        ")))),grid:(categoryLines:!f),labels:(),legendPosition:right" +
        ",seriesParams:!((data:(id:'1',label:'" + mode + "%20of%20va" +
        "lue'),drawLinesBetweenPoints:!t,interpolate:linear,lineWidt" +
        "h:2,mode:normal,show:!t,showCircles:!t,type:line,valueAxis:" +
        "ValueAxis-1)),thresholdLine:(color:%23E7664C,show:!f,style:" +
        "full,value:10,width:1),times:!(),type:line,valueAxes:!((id:" +
        "ValueAxis-1,labels:(filter:!f,rotate:0,show:!t,truncate:100" +
        "),name:LeftAxis-1,position:left,scale:(mode:normal,type:lin" +
        "ear),show:!t,style:(),title:(text:'" + mode + "%20of%20valu" +
        "e'),type:value))),title:" + title + ",type:line))";
    return url;
}

/**
 * used for job creation at server-side
 *
 * @param {Object} job_type - Federation job's type like data_join and so on
 * @param {Object} start_time - Data's start time like "2020-08-19T09:42:04.402Z"
 * @param {Object} end_time - Data's end time like "2020-08-19T09:42:40.368Z"
 * @param {Object} application_id - Job's application id
 * @return {Object} - list of metrics chart urls
 */
function converted2Urls(job_type, start_time, end_time, application_id) {
    let urls = [];
    for(let i = 0; i <metrics_list[job_type].length; ++i){
        let url = converted2Url(start_time, end_time, application_id,
                                metrics_list[job_type][i]["query"],
                                metrics_list[job_type][i]["mode"],
                                metrics_list[job_type][i]["title"]);
        urls.push(url);
    }
    return urls;
}