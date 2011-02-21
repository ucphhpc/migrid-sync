<!--
Name: KUnet Login
Description: Basic KUnet login wrapper to avoid repeated typing of silly username
Requires: jquery.js
-->
<script src="https://intranet.ku.dk/CookieAuth.dll?GetPic?formdir=8&image=flogon.js" type="text/javascript"></script>
<script type="text/javascript">
    $(document).ready(function() {
        // Specify your KU username once and for all here
        username="INSERT_YOUR_KU_USERNAME_HERE";
        $(".kunetlogin").html('<h2>KUnet login</h2><form action="https://intranet.ku.dk/CookieAuth.dll?Logon" method="post" id="logonForm" ><input id="rdoPrvt" type="hidden" name="trusted" value="4" /><input class="logininput" type="hidden" id="username" name="username" value="'+username+'" />pw: <input class="logininput" id="password" name="password" type="password" size="10"><input type="hidden" id="curl" name="curl" value="Z2FsiderZ2Fdefault.aspx" /><input type="hidden" id="flags" name="flags" value="0" /><input type="hidden" id="forcedownlevel" name="forcedownlevel" value="0" /><input type="hidden" id="formdir" name="formdir" value="8" /><input class="logininput loginsubmit" type="submit" value="Log in" onclick="clkLgn()" />');
    });
</script>
<div id="content">
    <div class="kunetlogin smallcontent">
        <p>Please enable Javascript to view this kunetlogin widget.</p>
    </div>
</div>
