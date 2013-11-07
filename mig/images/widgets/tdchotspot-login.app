<!--
Name: TDC Hotspot Login
Description: Basic TDC Hotspot login wrapper for convenient direct login
Requires: jquery.js
-->
<script type="text/javascript" src="hotspots.js"></script>
<script type="text/javascript" src="lcp.js"></script>
<script type="text/javascript">
    $(document).ready(function() {
        /* 
	   Specify your cell phone number as username once and for all here
	   to avoid typing it each time.
	   Optionally you can add your password as well, but please
	   beware that it will be saved in *unencrypted* form on the MiG
	   server then. This still means that it will be certificate
	   protected from anyone but the MiG admins. 
	   **************************************************************
	   * Save the password at your own risk - You have been warned! *
	   **************************************************************
	*/
        username="INSERT_YOUR_TDC_PHONE_NUMBER_HERE";
        password="";
        $(".tdchotspotlogin").html('<h2>TDC Hotspot login</h2><div class="tdchotspotinit"></div><div class="tdchotspotform"></div>');
        $(".tdchotspotinit").html('<button class="tdchotspotinitbutton t_button_grey"">Init first</button>');
        $(".tdchotspotform").html('<form name="loginform" class="t_block_login" method="post" action="https://redirect.tdchotspot.dk/sd/login"><label>Username</label><input id="username" name="username" size=10 style="display: block;" value="'+username+'" type="text"><label>Password</label><input id="password" name="password" size=10 style="display: block;" type="password" value="'+password+'"><button class="t_button_gray" type="submit"><span>Log in</span></button></form>');
        $(".tdchotspotinitbutton").click(function() {
            $.get("https://redirect.tdchotspot.dk", function(data, status){
                // fire and forget - to init session
                //alert("DEBUG: Data: " + data + "\nStatus: " + status);
                alert("Init succeeded, now you can proceed with login");
            });
        });
    });
</script>
<div id="content">
    <div class="tdchotspotlogin smallcontent">
        <p>Please enable Javascript to view this tdchotspotlogin widget.</p>
    </div>
    <div>
        <a href="https://redirect.tdchotspot.dk/">Full login page</a>
    </div>
</div>
