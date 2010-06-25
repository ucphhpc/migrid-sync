/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/
XMLService=function (selfname)
{
    this.selfname=selfname;
    this.xmldoc=null;
    this.xmlparser=null;
}
XMLService.prototype.Init=function ()
{
    this.CreateParser();
}
XMLService.prototype.CreateParser=function ()
{
   if ( window.ActiveXObject ) {
       // IE style browser
        var ProgIDs=["Msxml2.DOMDocument.6.0","Msxml2.DOMDocument.3.0"];
        for(var i=0;i<ProgIDs.length;i++)
            try
            {
                this.xmldoc=new ActiveXObject(ProgIDs[i]);
                break;
            }catch(e){}
    }
    else if( window.DOMParser ) {
	// Mozilla style browser
        this.xmlparser=new DOMParser();
    }
    else {
	// not supported
        alert("create parser: Browser not supported for XML parsing.");
        this.xmlparser=null;
    }
}
XMLService.prototype.LoadXMLText=function (xml, async)
{
    if (!(this.xmlparser)) {
        alert("Load: Browser not supported for XML parsing.");
	return;
    }
    if(  window.ActiveXObject )
    {
        if(this.xmldoc.loadXML(xml)!=true)
            return this.xmldoc.parseError.errorCode+"\n"+this.xmldoc.parseError.reason+this.xmldoc.parseError.line+','+this.xmldoc.parseError.linepos;
    } else if( window.DOMParser )
    {
        this.xmldoc=this.xmlparser.parseFromString(xml,"text/xml");
	this.xmldoc.async=async;
    }
    else {
        // cannot be!
	alert("load xml: unexpected exception");
	return;
    }
}
XMLService.prototype.PackMessage=function (methodname, arguments)
{
    this.LoadXMLText('<?xml version="1.0"?><methodCall></methodCall>', false);
    var node1=this.xmldoc.createElement("methodName");
    var node2=this.xmldoc.createTextNode(methodname);
    node1.appendChild(node2);
    var node3=this.xmldoc.createElement("params");
    if(arguments==null)
    {
        var empty=this.xmldoc.createTextNode('');
        node3.appendChild(empty);
    }else
    {
        for(var i=0;i<arguments.length;i++)
        {
        var node4=this.xmldoc.createElement("param");
        var node5=this.xmldoc.createElement("value");
        node5.appendChild(this.PackAny(arguments[i],false));
        node4.appendChild(node5);
        node3.appendChild(node4);
        }
    }
    this.xmldoc.getElementsByTagName("methodCall")[0].appendChild(node1);
    this.xmldoc.getElementsByTagName("methodCall")[0].appendChild(node3);

    if ( window.ActiveXObject ) {
	return this.xmldoc.xml;
    }
    else if ( window.DOMParser ) {
	return (new XMLSerializer().serializeToString(this.xmldoc));
    }
    else {
	return "<ERROR/>";
    }
}
XMLService.prototype.UnpackMessage=function (xml)
{
    var a;
    var r=this.LoadXMLText(xml,false);
    if(typeof r!='undefined'){return r;}
    var root=this.xmldoc.documentElement;
    a=this.UnpackAny(root.getElementsByTagName('value')[0]);
    return a;
}

XMLService.prototype.UnpackAny=function (any)
{
    switch(any.nodeName)
    {
        case "value":
            return this.UnpackAny(any.childNodes[0]);
        case "string":
            return this.UnpackString(any);
        case "double":
        case "int":
        case "i4":
            return this.UnpackNumber(any);
        case "boolean":
        case "bool":
            return this.UnpackBoolean(any);
        case "dateTime.iso8601":
            return this.UnpackDate(any);
        case "array":
            return this.UnpackArray(any);
        case "struct":
            return this.UnpackObject(any);
    }
}

XMLService.prototype.PackAny=function (any, info)
{
        if(any instanceof String||typeof any == "string")
            return this.PackString(any);
        if(any instanceof Boolean||typeof any =="boolean")
            return this.PackBoolean(any);
        if(any instanceof Number||typeof any =="number")
            return this.PackNumber(any, info);
        if(any instanceof Date)
            return this.PackDate(any);
        if(any===null)
            return this.PackNull(any);
        if(any instanceof Array)
            return this.PackArray(any);
        if(any instanceof Object)
            return this.PackObject(any);
}

XMLService.prototype.PackNull=function (n)
{
    return this.xmldoc.createTextNode('');
}

XMLService.prototype.PackNumber=function(n, isDouble)
{
    if ( n % 1 != 0 || isDouble==true)
    {
        var node=this.xmldoc.createElement("double");
        var text=this.xmldoc.createTextNode(n);
        node.appendChild(text);
        return node;
    }
    else
    {
        var node=this.xmldoc.createElement("int");
        var text=this.xmldoc.createTextNode(n);
        node.appendChild(text);
        return node;
    }    
}
XMLService.prototype.UnpackNumber=function (node)
{
    var obj=new Number();
    switch(node.nodeName)
    {
        case "double":
            obj=parseFloat(this.NodeText(node));
        case "i4":
        case "int":
            obj=parseInt(this.NodeText(node));
    }
    return obj;
}
XMLService.prototype.PackDate=function (d)
{
    month=d.getMonth();
    day=d.getDay();
    hours=d.getHours();
    minutes=d.getMinutes();
    seconds=d.getSeconds();
    var node=this.xmldoc.createElement("dateTime.iso8601");
    var text=d.getFullYear()+(month<10?'0'+month:month)+(day<10?'0'+day:day)+'T'+(hours<10?'0'+hours:hours)+(minutes<10?'0'+minutes:minutes)+(seconds<10?'0'+seconds:seconds);
    node.appendChild(text);
    return node;
}
XMLService.prototype.UnpackDate=function (node)
{
    var txt=this.NodeText(node);
    var re=/^(\d{4})(\d{2})(\d{2})T(\d+):(\d+):(\d+)$/;
    var array=txt.match(re);
    var d=new Date();
    d.setFullYear(array[1],array[2],array[3]);
    d.setHours(array[4],array[5],array[6]);
    return d;
}
XMLService.prototype.PackString=function (s)
{
    var node=this.xmldoc.createElement("string");
    var text=this.xmldoc.createTextNode(s);
    node.appendChild(text);
    return node;
}
XMLService.prototype.UnpackString=function (node)
{
    if(node.hasChildNodes())
        return this.NodeText(node);
    else
        return '';
}
XMLService.prototype.PackBoolean=function (b)
{
    var node=this.xmldoc.createElement("boolean");
    var text=this.xmldoc.createTextNode(b);
    node.appendChild(text);
    return node;
}
XMLService.prototype.UnpackBoolean=function (node)
{
    return this.NodeText(node).toLowerCase()=='true'?true:false;
}
XMLService.prototype.PackArray=function (a)
{
    var node=this.xmldoc.createElement("array");
    var data=this.xmldoc.createElement("data");
    var value;
    for ( var i = 0; i < a.length; i++ )
    {
        value=this.xmldoc.createElement("value");
        text=this.PackAny(a[i], false);
        value.appendChild(text);
        data.appendChild(value);
    }
    node.appendChild(data);
    return node;
}
XMLService.prototype.UnpackArray=function (node)
{
    var a=new Array();
    for(var i=0;i<this.ChildNodes(this.ChildNodes(node, "data")[0],"value").length;i++)
        a[i]=this.UnpackAny(this.ChildNodes(this.ChildNodes(node, "data")[0],"value")[i]);
    return a;
}
XMLService.prototype.PackObject=function (o)
{
    var node=this.xmldoc.createElement("struct");
    var member;
    var name;
    var value;
    var j=0;
    for (var i in o)
    {
        if(typeof i !="function")
        {
        member=this.xmldoc.createElement("member");
        name=this.xmldoc.createElement("name");
        value=this.xmldoc.createElement("value");
        text1=this.PackAny(o[i], false);
        text2=this.xmldoc.createTextNode(i);
        value.appendChild(text1);
        name.appendChild(text2);
        member.appendChild(name);
        member.appendChild(value);
        node.appendChild(member);
        j++;
        }
    }
    if(j==0)
    {
        var empty=this.xmldoc.createTextNode('');
        node.appendChild(empty);
    }
    return node;
}
XMLService.prototype.UnpackObject=function (node)
{
    var o=new Object();
    var name;
    var value;
    for(var i=0;i<this.ChildNodes(node, "member").length;i++)
    {
        name=this.NodeText(this.ChildNodes(this.ChildNodes(node, "member")[i],"name")[0]);
        value=this.UnpackAny(this.ChildNodes(this.ChildNodes(node, "member")[i],"value")[0]);
        o[name]=value;
    }
    return o;
}
XMLService.prototype.ChildNodes=function (node, name)
{
    var nodes=[];
    for(var i=0;i<node.childNodes.length;i++)
        if(node.childNodes[i].nodeName==name)
            nodes.push(node.childNodes[i]);
    return nodes;
}
XMLService.prototype.NodeText=function (node)
{
    return node.childNodes[0].nodeValue;
}

AjaxService=function (selfname, serviceurl)
{
    this.serviceurl=serviceurl;
    this.selfname=selfname;
}

AjaxService.prototype.Init=function ()
{
    this.xmlresponse=null;
    this.xmlhttprequest=null;
    this.xmlservice=new XMLService(this.selfname+".xmlservice");
    this.xmlservice.Init();
    this.CreateXMLHttpRequest();
}

AjaxService.prototype.CreateXMLHttpRequest = function()
{
    if (window.XMLHttpRequest) {
        this.xmlhttprequest = new XMLHttpRequest();
    }
    if (!this.xmlhttprequest&&window.ActiveXObject)
    {
        var ProgIDs=["Msxml2.XMLHTTP.6.0","Msxml2.XMLHTTP.5.0","Msxml2.XMLHTTP.4.0","Msxml2.XMLHTTP.3.0","Msxml2.XMLHTTP","Microsoft.XMLHTTP"];
        for(var i=0;i<ProgIDs.length;i++)
        try
        {
            this.xmlhttprequest = new ActiveXObject(ProgIDs[i]);
            break;
        }
        catch(e){}
    }
}

AjaxService.prototype.Post = function( serviceurl, content, contenttype )
{
    if ( typeof this.xmlhttprequest.abort == 'function' && this.xmlhttprequest.readyState != 0 )
    {
        this.xmlhttprequest.abort();
    }
    try
    {this.xmlhttprequest.open( 'POST', serviceurl, false );}
    catch(e)
        {alert("XMLHttpRequest POST failed!");}
    if ( typeof this.xmlhttprequest.setRequestHeader == 'function' )
    {
        this.xmlhttprequest.setRequestHeader('Content-Type',contenttype );
    }
    this.xmlhttprequest.send( content );
    this.xmlresponse = this.xmlhttprequest.responseXML;
    return this.xmlhttprequest.responseText;
}

AjaxService.prototype.Invoke = function(method, arguments)
{
    var content=this.xmlservice.PackMessage(method, arguments);
    var r=this.Post( this.serviceurl, content, 'text/xml' );
    return this.xmlservice.UnpackMessage(r);
}
