/*
MiG Advanced Shell
Nov, 2009 by Yang Zhao (student@live.cn)
License: GPL v2
This is a subproject affiliated to Minimium Intrusion Grid (MiG) directed by Prof. Brian Vinter.
The purpose is to improve web UI and provide a managerial shortcut for trivial operations.
*/

/*
Output - To show javascript objects. 
The objects are structurally parsed from corresponding XMLRPC response.
*/
Output=function(selfname)
{
    this.selfname=selfname;
    this.gui=null;
}
Output.prototype.Init=function(gui)
{
    this.gui=gui;
}
/*
Output.Accept(result)
result - the javascript object returned by the XMLRPC component.
*/
Output.prototype.Accept=function(result)
{
    //valid result layout: [[{},{},...],[exitcode:int, state:string]]
    if(Type(result)=='ARRAY'&&result.length==2)
    {
        if(Type(result[0])=='ARRAY'&&Type(result[1])=='ARRAY')
            {
                for(var i=0;i<result[0].length;i++)
                    this.ObjectFilter(result[0][i]);
                this.StateFilter(result[1]);
            }
    }
    else
    {
        this.gui.Output(ShowObject(result));
    }
}
/*
Output.StateFilter(state)
state - exitcode and state
*/
Output.prototype.StateFilter=function(state)
{
    //valid state layout: [exitcode:int, state:string]
    if(state[0]==0&&state[1]=='OK')
        return 0;
    else
    {
        this.gui.Output('state: '+state[0]+', description: '+state[1]);
        return -1;
    }
}
/*
Output.ObjectFilter(obj)
obj - javascript objects to show
*/
Output.prototype.ObjectFilter=function(obj)
{
    if(obj.hasOwnProperty('object_type'))
    {
        switch(obj.object_type)
        {
            case 'text':
                this.gui.Output(obj.text);
                break;
            case 'warning':
                this.gui.Output('Warning: '+obj.text);
                break;
            case 'error_text':
                this.gui.Output('Error: '+obj.text);
                break;
            case 'dir_listings':
                for(var i=0;i<obj.dir_listings.length;i++)
                {
                    this.ObjectFilter(obj.dir_listings[i]);
                }
                break;
            case 'dir_listing':
                var table=this.gui.CreateTable(obj.entries.length, 2);
                var j=0;
                for(var i=0;i<obj.entries.length;i++)
                {
                    if(obj.entries[i].type.toLowerCase()=='directory')
                    {
                        this.gui.FillTable(table, j, 0, obj.entries[i].name);
                        this.gui.FillTable(table, j, 1, '<dir>');
                        j++;
                    }
                }
                for(var i=0;i<obj.entries.length;i++)
                {
                    if(obj.entries[i].type.toLowerCase()=='file')
                    {
                    this.gui.FillTable(table, j, 0, obj.entries[i].name);
                    this.gui.FillTable(table, j, 1, '<file>');
                    j++;
                    }
                }
                this.gui.Output(table);
                break;
            case 'file_output':
                for(var i=0;i<obj.lines.length;i++)
                    this.gui.Output(obj.lines[i]);
                break;
            case 'file':
                this.gui.Output(obj.name);
                break;
            case 'filewcs':
                var table=this.gui.CreateTable(obj.filewcs.length, 4);
                for(var i=0;i<obj.filewcs.length;i++)
                {
                    this.gui.FillTable(table, i, 0, obj.filewcs[i].name);
                    this.gui.FillTable(table, i, 1, '<'+obj.filewcs[i].bytes+' bytes>');
                    this.gui.FillTable(table, i, 2, '<'+obj.filewcs[i].words+' words>');
                    this.gui.FillTable(table, i, 3, '<'+obj.filewcs[i].lines+' lines>');
                }
                this.gui.Output(table);
                break;
            case 'file_not_found':
                this.gui.Output('File: '+obj.name+' not found!');
                break;
            case 'job_list':
                var jobs=obj.jobs;
                var table=this.gui.CreateTable(jobs.length, 3)//job_id, status, time_stamp
                for(var i=0;i<jobs.length;i++)
                {
                    this.gui.FillTable(table, i, 0, jobs[i].job_id);
                    this.gui.FillTable(table, i, 1, jobs[i].status);
                    this.gui.FillTable(table, i, 2, jobs[i].received_timestamp);
                }
                this.gui.Output(table);
                break;
            case 'link':
                //TODO
            case 'list':
                //TODO
            case 'resubmitobjs':
                //TODO
            case 'stats':
                //TODO
            case 'submitstatuslist':
                //TODO
                this.gui.Output("No display for object type: "+obj.object_type+".");
                this.gui.Output(ShowObject(obj));
        }
    }
}
