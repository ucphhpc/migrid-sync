/* TODO this file is currently unused! Should take
 * the code inside jobman.py.
 */

if (jQuery) (function($){
  
  $.fn.jobmanager = function(user_options) {

    var defaults = {
      connector: 'jobs/index',
      expandSpeed: 500,
      collapseSpeed: 500,
      expandEasing: null,
      collapseEasing: null,
      loadMessage: 'Loading...'
    };
    var options = $.extend(defaults, user_options);

    
    return this.each(function() {
      obj = $(this);
            
      $.getJSON(options.connector, {}, function(jsonRes, textStatus) {
      
        var jobList = new Array();          
        var i =0;
        
        // Grab jobs from json response and place them in jobList.
        for(i=0; i<jsonRes.length; i++) {
          if (jsonRes[i].object_type == 'job_list') {              
            jobList = jobList.concat(jsonRes[i].jobs);
          }
        }
        
        $('.jobs').html('');
        
        $.each(jobList, function(i, item) {
          
          $('.jobs', obj).append('<tr>'+
                                 '<td>'+item.job_id+'</td>'+
                                 '<td>'+item.status+'</td>'+
                                 '<td><a href="'+item.mrsllink.destination+'">mRSL</a></td>'+
                                 '<td><a href="'+item.statuslink.destination+'">status</a></td>'+
                                 '<td><a href="'+item.jobschedulelink.destination+'">schedule</a></td>'+
                                 '<td>'+item.received_timestamp+'</td>'+
                                 '<td><a href="'+item.cancellink.destination+'">cancel</a></td>'+
                                 '<td><a href="'+item.liveoutputlink.destination+'">liveout</a></td>'+
                                 //'<a href="'+item.outputfileslink.destination+'">outputfiles</a></td>'+
                                 '<td><a href="'+item.resubmitlink.destination+'">resubmitlink</a></td>'+
                                 '</tr>'
                                 
                                 );
          
          
        });
        
        //$('.jobs tr').selectable();
        
      });

    });

 };
 
})(jQuery);
