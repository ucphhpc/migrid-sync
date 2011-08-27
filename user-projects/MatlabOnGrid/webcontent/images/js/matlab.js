
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
    });
	
}


$(document).ready(function(){
	
	$( "#info_dialog").dialog({
		autoOpen: false,
		show: "fade"
		//hide: "slide" 
		//position:"top"
	});
	
	$(".addinputfile").click(function(){
		add_form_input();
	});
	
	
	$("#compile_button").click(function(){
		$("#compile_output").html = "compiling.....";
	});
		
	
	/*$(".remove_file").click(function(){
		alert("click");
		//$(this).hide();
	});
	*/
	
	
	$("#info_local").hover(function(e){
		//alert(e.PageX);
		$("#info_dialog").html("Excute the grid jobs only on the server. This ensures faster response times for debugging. Use only for testing and with small jobs.");
		$("#info_dialog").dialog( "option" , "position" , [e.pageX, e.pageY]);
		$("#info_dialog").dialog( "option" , "closeText" , "");
		
		$("#info_dialog").dialog("open");
		
	},
	function(){
		$("#info_dialog").dialog("close");
		
		});
	
	
	$("input[type=submit]").click(function(){
		$("input").disable();
		
		//$("#submit_output").append(<>);
		return true;
	});
	
	
	  $(".cancel").click(function(){
          var name = $(this).attr("solvername");
          cancel_process(name);
	  });
	
	
});
