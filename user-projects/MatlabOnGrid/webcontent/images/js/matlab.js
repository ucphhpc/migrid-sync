
function add_form_input(){
	var num_files = $("input[type='file']").length;
	var input_id = "input_file"+num_files;
	//var html = "<div id='"+input_id+"'> Choose file nr. "+num_files+" : <input name='file"+num_files+"' type='file' value='' /> <div class='remove_file' id='"+input_id+"' onClick='delete_form_input("+num_+)'>remove</div></div>";
	var html = "<div id='"+input_id+"'> Choose file nr. "+num_files+" : <input name='file"+num_files+"' type='file' value='' /> </div>";
	$(".inputfiles").append(html);
}


function delete_form_input(){
	alert($(this).html());
	$(this).remove();
}



function cancel_process(name){
	var url = "/cgi-bin/cancel.py";
    var query = {'name':name, 'output_format':'json'};
    $.getJSON(url, query, function(jsonRes, status) {
    //alert(jsonRes.length);
      //for (var i = 0; i < jsonRes.length; i++) {
      //if(jsonRes[i] == "text"){
         alert(jsonRes[0].text);
      //     }
      //}
         
	window.location.reload();

    });
}

function delete_process(name){
	if(confirm("Delete entry including output files : "+name)){
		var url = "/cgi-bin/delete_process.py";
	    var query = {'name':name, 'output_format':'json'};
	    $.getJSON(url, query, function(jsonRes, status) {
					alert(jsonRes[0].text);
					window.location.reload();
					if(jsonRes.status){
						// remove the file we just deleted from the list
						//var selstr = "a:contains('"+jsonRes.name+"')";
						//$(selstr).parent().parent().hide(); // select the row
						
					}
				});
	 		}
	  }
	

function executable_ready(){
	var url = "/cgi-bin/executable_ready.py";
    var query = {'output_format':'json'};
    $.getJSON(url, query, function(jsonRes, status) {
    //alert(jsonRes.length);
      //for (var i = 0; i < jsonRes.length; i++) {
      //if(jsonRes[i] == "text"){
    	
    	 
        //alert(jsonRes[0].text);
    	
    	if(jsonRes[0].ready == "1"){
    		$("#submit_status").append("A compiled matlab program is ready to be submitted. compiled on "+jsonRes[0].modified+".");
    	} 
    	else{
    		$("#submit_status").css("color","red");
    		$("#submit_status").append("Please compile a matlab file first.");
    		
    	}	
    	
    	
      //     }
      //}
         
	//window.location.reload();

    });
}




$(document).ready(function(){
	
	$("#compile_output").hide();
	$("#submit_output").hide();
	
	
	$( "#info_dialog").dialog({
		autoOpen: false,
		show: "fade"
		//hide: "slide" 
		//position:"top"
	});
	
	$(".addinputfile").click(function(){
		add_form_input();
	});
	
	
	/*$(".compile_button").click(function(){
		alert("h");
		$("#compile_output").html("compiling.....");
	});
	*/
	
	$("#compile_form").submit(function(){
		//$("#compile_output").html("<html><body>compiling....</body></html>");
		
		// NOTE: this is a bit of a hack i guess for reason 
		// $("#compile_output").html("<html><body>compiling....</body></html>") 
		// does not work.
		 $("#compile_output").show();
		 var ifrm = document.getElementById('compile_output');
         ifrm = (ifrm.contentWindow) ? ifrm.contentWindow : (ifrm.contentDocument.document) ? ifrm.contentDocument.document : ifrm.contentDocument;
         ifrm.document.open();
         ifrm.document.write('MCC is compiling on the server. Takes around 10-20 seconds<blink>...</blink>');
         ifrm.document.close();
//		$("#compile_output").attr("src",$("#compile_output").attr("src"));
		//var frame = $("#compile_output");
		//var doc = frame[0].contentWindow.document;
		//$(frame, doc).attr("src","whatever");
		//frame.reload();
		//alert($("#compile_output").html());
		
		//$("#compile_output").html("compiling.....");
	});
	
	
	/*$(".remove_file").click(function(){
		alert("click");
		//$(this).hide();
	});
	*/
	
	
	$("#info_icon").hover(function(e){
		
		$("#info_dialog").html("Execute the grid jobs only on the server. This ensures faster response times for debugging. Use only for testing and with small jobs.");
		$("#info_dialog").dialog( "option" , "position" , [e.pageX, e.pageY]);
		$("#info_dialog").dialog( "option" , "closeText" , "");
		
		$("#info_dialog").dialog("open");
		
	},
	function(){
		$("#info_dialog").dialog("close");
		
		});
	
	
	/*$("input[type=submit]").click(function(){
		$("input").disable();
		alert("sub2");
		//$("#submit_output").append(<>);
		return true;
	});
	*/
	$("#submit_form").submit(function(){
		$("input").prop('readonly', "readonly");
		$("input[type=submit]").prop("disabled","disabled"); 
		$("#submit_output").show();
		 var ifrm = document.getElementById('submit_output');
         ifrm = (ifrm.contentWindow) ? ifrm.contentWindow : (ifrm.contentDocument.document) ? ifrm.contentDocument.document : ifrm.contentDocument;
         ifrm.document.open();
         ifrm.document.write('Server is starting jobs<blink>...</blink>');
         ifrm.document.close();
		//alert("sub2");
		//$("#submit_output").append(<>);
		//return true;
	});
	
	
	  $(".cancel").click(function(){
          var name = $(this).attr("solvername");
          cancel_process(name);
	  });
	
	
	  $("img#delete_process").each(function(){
		  $(this).hover(function(){
			$(this).css('cursor','pointer');
			$(this).width($(this).width()*1.2);
			},function(){
			$(this).width($(this).width()/1.2);
		});
	  });
		    
		    
	  $("img#delete_process").click(function(){
			  delete_process($(this).attr("filename"));
	  });
	  
	  
});
