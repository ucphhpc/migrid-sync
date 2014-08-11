<!-- 
Name: Portlets
Author: Jonas Bardino <bardino AT nbi DOT ku DOT dk>
License: GPLv2
Description: Movable portlets using the JQuery UI Sortable widget (modification of portlets demo)
Requires: jquery.js, jquery-ui.js, jquery-ui.css, jquery-ui-theme.css, jquery-ui-theme.custom.css
-->
<style type="text/css">
.portletarea { width: 100%; float: right; }
.sortcolumn { width: 200px; float: left; padding-bottom: 100px; }
.portlet { margin: 0 1em 1em 0; }
.portlet-header { margin: 0.3em; padding-bottom: 4px;
padding-left: 0.2em; }
.portlet-header .ui-icon { float: right; }
.portlet-content { padding: 0.4em; }
.ui-sortable-placeholder { border: 1px dotted black; visibility:
visible !important; height: 50px !important; }
.ui-sortable-placeholder * { visibility: hidden; }
</style>
<script type="text/javascript">
$(function() {
    $(".sortcolumn").sortable({connectWith: '.sortcolumn'});
    $(".portlet").addClass("ui-widget ui-widget-content ui-helper-clearfix ui-corner-all")
                 .find(".portlet-header")
                 .addClass("ui-widget-header ui-corner-all")
                 .prepend('<span class="ui-icon ui-icon-minusthick"></span>')
                 .end()
                 .find(".portlet-content");
    $(".portlet-header .ui-icon").click(function() {
        $(this).toggleClass("ui-icon-minusthick").toggleClass("ui-icon-plusthick");
        $(this).parents(".portlet:first").find(".portlet-content").toggle();
    });  
    $(".sortcolumn").disableSelection();
});
</script>
<div class="portletarea">
<div class="sortcolumn">
     <div class="portlet">
          <div class="portlet-header">Feeds</div>
          <div class="portlet-content">Lorem ipsum dolor sit amet, consectetuer adipiscing elit</div>
     </div>
     <div class="portlet">
          <div class="portlet-header">News</div>
          <div class="portlet-content">Lorem ipsum dolor sit amet, consectetuer adipiscing elit</div>
     </div>
</div>
<div class="sortcolumn">
     <div class="portlet">
          <div class="portlet-header">Shopping</div>
          <div class="portlet-content">Lorem ipsum dolor sit amet, consectetuer adipiscing elit</div>
     </div>
</div>
<div class="sortcolumn">
     <div class="portlet">
          <div class="portlet-header">Links</div>
          <div class="portlet-content">Lorem ipsum dolor sit amet, consectetuer adipiscing elit</div>
     </div>
     <div class="portlet">
          <div class="portlet-header">Images</div>
          <div class="portlet-content">Lorem ipsum dolor sit amet, consectetuer adipiscing elit</div>
     </div>
</div>
</div>
<div id="portlettext">
<p>
Drag the portlets around as you like to select new positions or use the minimize
icon to hide their contents.
The portlets are simple wrappers that can hold *any* other widget
instead of the dummy text.
</p>
</div>
