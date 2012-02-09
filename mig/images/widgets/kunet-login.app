<!--
Name: KUnet Login
Description: Basic KUnet login wrapper to avoid repeated typing of silly username
Requires: jquery.js
-->
<script src="https://intranet.ku.dk/CookieAuth.dll?GetPic?formdir=8&image=flogon.js" type="text/javascript"></script>
<script type="text/javascript">
    $(document).ready(function() {
        /* 
	   Specify your auto-generated KU username once and for all here
	   to avoid having to remember it.
	   Optionally you can add your password as well, but please
	   beware that it will be saved in *unencrypted* form on the MiG
	   server then. This still means that it will be certificate
	   protected from anyone but the MiG admins. 
	   **************************************************************
	   * Save the password at your own risk - You have been warned! *
	   **************************************************************
	*/
        username="INSERT_YOUR_KU_USERNAME_HERE";
        password="";
	$(".kunetlogin").html('<h2>KUnet login</h2><form action="https://intranet.ku.dk/CookieAuth.dll?Logon" method="post" id="logonForm" ><input id="rdoPrvt" type="hidden" name="trusted" value="4" />username:<br /><input class="logininput" type="text" size="10" id="username" name="username" value="'+username+'" /><br />password:<br /><input class="logininput" id="password" name="password" type="password" size="10" value="'+password+'"><input type="hidden" id="curl" name="curl" value="Z2FSiderZ2Fdefault.aspx" /><input type="hidden" id="flags" name="flags" value="0" /><input type="hidden" id="forcedownlevel" name="forcedownlevel" value="0" /><input type="hidden" id="formdir" name="formdir" value="7" /><input class="logininput loginsubmit" type="submit" value="Log in" onclick="clkLgn()" /></form>');
    });
</script>
<div id="content">
    <div class="kunetlogin smallcontent">
        <p>Please enable Javascript to view this kunetlogin widget.</p>
    </div>
    <div class="kunetlinks smallcontent">
    	 <!---
	   You may want to add one or more links to e.g. Absalon pages
           here for easy access. That will provide easy access to
	   e.g. forum pages that otherwise time out frequently and force
	   repeated login.
	--->
    </div>
</div>
