// Copyright 2001 Idocs.com      
// Distribute this script freely, but keep this notice in place

// backlink object initializer
function backlink() {
	this.text = 'Go Back';
	this.type = 'link';
	this.write = backlink_write;
	this.form = true;
}


// write method
function backlink_write() {
	if (! window.history) return;
	if (window.history.length == 0)return;

	this.type = this.type.toLowerCase();
	if (this.type == 'button') {
		if (this.form)
			document.write('<FORM>');
		document.write('<INPUT TYPE=BUTTON onClick="history.back(-1)" VALUE="', this.text, '"');
		if (this.otheratts) document.write(' ', this.otheratts);
		document.write('>');
		if (this.form)document.write('<\/FORM>');
	} else {
		document.write('<A HREF="javascript:history.back(-1)"');
		if (this.otheratts)
			document.write(' ', this.otheratts);
		document.write('>');
		if (this.type == 'image' || this.type == 'img') {
			document.write('<img SRC="', this.src, '" ALT="', this.text, '"');
			if (this.width) document.write(' WIDTH=', this.width);
			if (this.height) document.write(' HEIGHT=', this.height);
			if (this.otherimgatts) document.write(' ', this.otherimgatts);
			document.write(' BORDER=0 />');
		}
		else
			document.write(this.text);
		document.write('<\/A>');
	}
}
