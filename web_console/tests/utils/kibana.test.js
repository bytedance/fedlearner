const assert = require('assert');
const { converted2Url } = require('../../utils/kibana');

describe('converted2Url', () => {
    it('should generate auc url', () => {
        const query = "name%20:%22auc%22";
        const mode = "avg";
        const title = "auc";
        const start_time = "2020-08-19T09:42:04.402Z";
        const end_time = "2020-08-19T09:42:40.368Z";
        const application_id = "test_app2";
        const url = "http://ad-kibana.bytedance.net/fedlearner/app/kibana#/visualize/edit/95e50f80-dd3a-11ea-a472-39251c5aaace?embed=true&_g=(filters:!(),refreshInterval:(pause:!t,value:0),time:(from:'2020-08-19T09:42:04.402Z',to:'2020-08-19T09:42:40.368Z'))&_a=(filters:!(('$state':(store:appState),meta:(alias:!n,disabled:!f,index:'73340100-dd33-11ea-a472-39251c5aaace',key:tags.application_id,negate:!f,params:(query:test_app2),type:phrase),query:(match_phrase:(tags.application_id:test_app2)))),linked:!f,query:(language:kuery,query:'name%20:%22auc%22'),uiState:(),vis:(aggs:!((enabled:!t,id:'1',params:(field:value),schema:metric,type:avg),(enabled:!t,id:'2',params:(drop_partials:!f,extended_bounds:(),field:date_time,interval:auto,min_doc_count:1,scaleMetricValues:!f,timeRange:(from:'2020-08-19T09:42:04.402Z',to:'2020-08-19T09:42:40.368Z'),useNormalizedEsInterval:!t),schema:segment,type:date_histogram),(enabled:!t,id:'3',params:(field:name.keyword,missingBucket:!f,missingBucketLabel:Missing,order:desc,orderBy:'1',otherBucket:!f,otherBucketLabel:Other,size:5),schema:group,type:terms)),params:(addLegend:!t,addTimeMarker:!f,addTooltip:!t,categoryAxes:!((id:CategoryAxis-1,labels:(filter:!t,show:!t,truncate:100),position:bottom,scale:(type:linear),show:!t,style:(),title:(),type:category)),dimensions:(series:!((accessor:1,aggType:terms,format:(id:terms,params:(id:string,missingBucketLabel:Missing,otherBucketLabel:Other,parsedUrl:(basePath:%2Ffedlearner,origin:'http:%2F%2Fad-kibana.bytedance.net',pathname:%2Ffedlearner%2Fapp%2Fkibana))),label:'name.keyword:%20Descending',params:())),x:(accessor:0,aggType:date_histogram,format:(id:date,params:(pattern:'HH:mm:ss')),label:'date_time%20per%20second',params:(bounds:(max:'2020-08-19T09:42:40.368Z',min:'2020-08-19T09:42:04.402Z'),date:!t,format:'HH:mm:ss',interval:PT1S,intervalESUnit:s,intervalESValue:1)),y:!((accessor:2,aggType:avg,format:(id:number,params:(parsedUrl:(basePath:%2Ffedlearner,origin:'http:%2F%2Fad-kibana.bytedance.net',pathname:%2Ffedlearner%2Fapp%2Fkibana))),label:'Average%20value',params:()))),grid:(categoryLines:!f),labels:(),legendPosition:right,seriesParams:!((data:(id:'1',label:'avg%20of%20value'),drawLinesBetweenPoints:!t,interpolate:linear,lineWidth:2,mode:normal,show:!t,showCircles:!t,type:line,valueAxis:ValueAxis-1)),thresholdLine:(color:%23E7664C,show:!f,style:full,value:10,width:1),times:!(),type:line,valueAxes:!((id:ValueAxis-1,labels:(filter:!f,rotate:0,show:!t,truncate:100),name:LeftAxis-1,position:left,scale:(mode:normal,type:linear),show:!t,style:(),title:(text:'avg%20of%20value'),type:value))),title:auc,type:line))";
        assert.deepStrictEqual(
            converted2Url(start_time, end_time, application_id,
                          query, mode, title),
            url,
        );
    });
});