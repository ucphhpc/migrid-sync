<!--
Name: KUnet Login
Description: Basic KUnet login wrapper to avoid repeated typing of silly username
Requires: jquery.js
-->
<script type="text/javascript">
    $(document).ready(function() {
        /*
           IMPORTANT: KU occasionally changes beween a 'secret' formdir
           variable value of 5 or 8. Change below if login fails with page error.
        */
        var formdir="5";
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
        var username="INSERT_YOUR_KU_USERNAME_HERE";
        var password="";
        /*** No more script changes should be needed after this line ***/
        /*  Load KUNet login helper script */
        var auth_url = "https://intranet.ku.dk/CookieAuth.dll";
        var script_url = auth_url+"?GetPic?formdir="+formdir+"&image=flogon.js";
        var script = document.createElement("script");
        script.setAttribute("type","text/javascript");
        script.setAttribute("src", script_url);
        document.getElementsByTagName("head")[0].appendChild(script);
        var login_url = auth_url+"?Logon";
        $(".kunetlogin").html('<h2>KUnet login</h2><form action="'+login_url+'" method="post" id="logonForm" ><input id="rdoPrvt" type="hidden" name="trusted" value="4" />username:<br /><input class="logininput" type="text" size="10" id="username" name="username" value="'+username+'" /><br />password:<br /><input class="logininput" id="password" name="password" type="password" size="10" value="'+password+'"><input type="hidden" id="curl" name="curl" value="Z2FSiderZ2Fdefault.aspx" /><input type="hidden" id="flags" name="flags" value="0" /><input type="hidden" id="forcedownlevel" name="forcedownlevel" value="0" /><input type="hidden" id="formdir" name="formdir" value="'+formdir+'" /><input class="logininput loginsubmit" type="submit" value="Log in" onclick="clkLgn()" /></form>');
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
