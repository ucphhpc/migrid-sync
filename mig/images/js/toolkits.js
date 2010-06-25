/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/

function Type(obj)
{
    if(typeof obj=='string'||obj instanceof String)
        return 'STRING';
    else if(typeof obj=='number'||obj instanceof Number)
        return 'NUMBER';
    else if(typeof obj=='boolean'||obj instanceof Boolean)
        return 'BOOLEAN';
    else if(obj instanceof Date)
        return 'DATE';
    else if(obj instanceof Array)
        return 'ARRAY';
    else if(obj===null)
        return 'NULL';
    else if(typeof obj=='object')
        return 'STRUCT';
}
function ShowObject(obj)
{
    var str='';
    switch(Type(obj))
    {
        case "STRING":
            str+=('"'+obj+'"');
            return str;
        case "NUMBER":
        case "BOOLEAN":
            str+=obj;
            return str;
        case "ARRAY":
            str+='[';
            var flag=false;
            for(var i=0;i<obj.length;i++)
            {
                str+=(ShowObject(obj[i])+',');flag=true;
            }
            if(flag==true)
                str=str.substr(0,str.length-1);
            str+=']';
            return str;
        case "STRUCT":
            str+='{';
            var flag=false;
            for(i in obj)
            {
                str+=(i+':'+ShowObject(obj[i])+','); flag=true;
            }
            if(flag==true)
                str=str.substr(0,str.length-1);
            str+='}';
            return str;
    }
    return str;
}
function SplitCmd (str)
{
    var re=new RegExp('".*?"','g');
    var quoted=str.match(re);
    var subsplit=function(str, parts, result)
    {
        if(str=='')
            return result;
        for(var i in parts)
        {
            if(parts[i])
            {
                var re=new RegExp('[ ]*'+parts[i].replace(/\\/g, '\\\\')+'[ ]*');
                if(str.search(re)==0)
                {
                    var tmp=str.match(re);
                    var r=new RegExp('^"(.*)"$');
                    var x=parts[i].match(r);
                    result.push(x?x[1]:parts[i]);
                    parts[i]=null;
                    return arguments.callee(str.slice(tmp[0].length), parts, result); // recursive point for anonymous function
                }
            }
        }
    }
    if(quoted)
    {
        var parts=str.replace(re, '');
        parts=parts.split(/\s+/);
        parts=parts.concat(quoted);
        var result=subsplit(str, parts, []);
    }
    else
    {
        var result=str.split(/\s+/);
    }
    return result;
}
