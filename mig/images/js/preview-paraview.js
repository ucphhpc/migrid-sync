/*

#
# --- BEGIN_HEADER ---
#
# paraview - ParaviewWeb render library
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public Licethnse as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

*/

/*

This module is based on PreviewParaviewWeb: http://paraviewweb.kitware.com/

ParaView License: http://www.paraview.org/paraview-license

ParaView uses a permissive BSD license that enables 
the broadest possible audience, including commercial organizations, 
to use the software, royalty free, for most purposes. 
In addition, there are other licenses that are applicable 
because of other packages leveraged by ParaView or developed by collaborators.
Lastly, there are specific packages for the ParaView binaries available 
on paraview.org that have applicable licenses.  
These additional licenses are detailed at the bottom of this page.
Copyright (c) 2005-2008 Sandia Corporation, Kitware Inc.
Sandia National Laboratories, New Mexico PO Box 5800 Albuquerque, NM 87185
Kitware Inc., 28 Corporate Drive, Clifton Park, NY 12065, USA

Under the terms of Contract DE-AC04-94AL85000, 
there is a non-exclusive license for use of this work 
by or on behalf of the U.S. Government.

Redistribution and use in source and binary forms, 
with or without modification, are permitted provided that 
the following conditions are met:

Redistributions of source code must retain the above copyright notice, 
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, 
this list of conditions and the following disclaimer in the documentation 
and/or other materials provided with the distribution.
    
Neither the name of Kitware nor the names of any contributors 
may be used to endorse or promote products derived from this software
without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, 
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS 
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
IN NO EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) 
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, 
EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
http://www.paraview.org/paraview-license/

Copyright (c) 2010, Ryan LeFevre
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of Ryan LeFevre nor the names of its contributors may be 
      used to endorse or promote products derived from this software without
      specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; 
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) 
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

*/

/*! vtkWeb/ParaViewWeb - v2.0 - 2015-08-06
* http://www.kitware.com/
* Copyright (c) 2015 Kitware; Licensed BSD */
/**
 * vtkWebLoader JavaScript Library.
 *
 * vtkWebLoader use the vtkWeb namespace to manage JavaScript dependency and more specifically
 * vtkWeb dependencies.
 *
 * @class vtkWebLoader
 *
 * @singleton
 *
 * ORG: /images/lib/ParaView/lib/core/vtkweb-loader.js
 *
 */
(function (GLOBAL) {
    AUTOBAHN_DEBUG = false;

    var vtkWebLibs = {
        "core" : [
        "/images/lib/ParaView/ext/core/autobahn.js",
        "/images/lib/ParaView/ext/core/gl-matrix.js",
        "/images/lib/ParaView/ext/core/jquery.hammer.js",
        "/images/lib/ParaView/ext/core/vgl.js",
        "/images/lib/ParaView/lib/core/vtkweb-all.js"
        ],
        "core-min": [
        "/images/lib/ParaView/ext/core/autobahn.min.js",
        "/images/lib/ParaView/ext/core/gl-matrix-min.js",
        "/images/lib/ParaView/ext/core/jquery.hammer.min.js",
        "/images/lib/ParaView/ext/core/vgl.min.js",
        "/images/lib/ParaView/lib/core/vtkweb-all.min.js"
        ],
        "bootstrap": [
        "/images/lib/ParaView/ext/bootstrap/js/bootstrap.min.js",
        "/images/lib/ParaView/ext/bootstrap/css/bootstrap-responsive.min.css",
        "/images/lib/ParaView/ext/bootstrap/css/bootstrap.min.css"
        ],
        "fontello": [
        "/images/lib/ParaView/ext/fontello/css/animation.css",
        "/images/lib/ParaView/ext/fontello/css/fontello.css"
        ],
        "color": [
        "/images/lib/ParaView/ext/jscolor/jscolor.js"
        ],
        "filebrowser": [
        "/images/lib/ParaView/ext/pure/pure.min.js",
        "/images/lib/ParaView/lib/widgets/FileBrowser/vtkweb-widget-filebrowser.js",
        "/images/lib/ParaView/lib/widgets/FileBrowser/vtkweb-widget-filebrowser.tpl",
        "/images/lib/ParaView/lib/widgets/FileBrowser/vtkweb-widget-filebrowser.css"
        ],
        "pv-pipeline": [
        "/images/lib/ParaView/ext/jquery-ui/jquery-ui-1.10.0.css",
        "/images/lib/ParaView/ext/jquery-ui/jquery-ui-1.10.0.min.js",
        "/images/lib/ParaView/lib/css/paraview.ui.pipeline.css",
        "/images/lib/ParaView/lib/js/paraview.ui.pipeline.js",
        ],
        "pv-toolbar": [
        "/images/lib/ParaView/lib/css/paraview.ui.toolbar.css",
        "/images/lib/ParaView/lib/css/paraview.ui.toolbar.vcr.css",
        "/images/lib/ParaView/lib/css/paraview.ui.toolbar.viewport.css",
        "/images/lib/ParaView/lib/css/paraview.ui.toolbar.connect.css",
        "/images/lib/ParaView/lib/js/paraview.ui.toolbar.js",
        "/images/lib/ParaView/lib/js/paraview.ui.toolbar.vcr.js",
        "/images/lib/ParaView/lib/js/paraview.ui.toolbar.viewport.js",
        "/images/lib/ParaView/lib/js/paraview.ui.toolbar.connect.js"
        ],
        "jquery-ui": [
        "/images/lib/ParaView/ext/jquery-ui/jquery-ui-1.10.0.css",
        "/images/lib/ParaView/ext/jquery-ui/jquery-ui-1.10.0.min.js"
        ],
        "d3":[
        "/images/lib/ParaView/ext/d3/d3.v2.js"
        ],
        "nvd3":[
        "/images/lib/ParaView/ext/nvd3/nv.d3.css",
        "/images/lib/ParaView/ext/nvd3/nv.d3.js"
        ],
        "rickshaw": [
        "/images/lib/ParaView/ext/rickshaw/rickshaw.min.css",
        "/images/lib/ParaView/ext/rickshaw/rickshaw.min.js"
        ],
        "widgets": [
        "/images/lib/ParaView/ext/pure/pure.min.js",
        "/images/lib/ParaView/ext/d3/d3.v2.js",
        "/images/lib/ParaView/ext/rickshaw/rickshaw.min.css",
        "/images/lib/ParaView/ext/rickshaw/rickshaw.min.js",
        "/images/lib/ParaView/ext/fontello/css/animation.css",
        "/images/lib/ParaView/ext/fontello/css/fontello.css",
        "/images/lib/ParaView/lib/widgets/FileBrowser/vtkweb-widget-filebrowser.tpl",
        "/images/lib/ParaView/lib/widgets/TreeWidget/vtkweb-widget-tree.tpl",
        "/images/lib/ParaView/lib/widgets/vtkweb-widgets-min.css",
        "/images/lib/ParaView/lib/widgets/vtkweb-widgets-min.js"
        ],
        "pv.visualizer": [
        "/images/lib/ParaView/ext/fontello/css/animation.css",
        "/images/lib/ParaView/ext/fontello/css/fontello.css",
        "/images/lib/ParaView/ext/bootstrap3/js/bootstrap.min.js",
        "/images/lib/ParaView/lib/js/paraview.ui.action.list.js",
        "/images/lib/ParaView/lib/js/paraview.ui.files.js",
        "/images/lib/ParaView/lib/js/paraview.ui.data.js",
        "/images/lib/ParaView/lib/js/paraview.ui.proxy.editor.js",
        "/images/lib/ParaView/lib/css/paraview.ui.proxy.editor.css",
        "/images/lib/ParaView/lib/js/paraview.ui.svg.pipeline.js",
        "/images/lib/ParaView/lib/js/paraview.ui.opacity.editor.js",
        "/images/lib/ParaView/lib/css/paraview.ui.opacity.editor.css",
        "/images/lib/ParaView/lib/js/paraview.ui.color.editor.js",
        "/images/lib/ParaView/lib/css/paraview.ui.color.editor.css"
        ]

    },
    modules = [],
    script = document.getElementsByTagName("script")[document.getElementsByTagName("script").length - 1],
    basePath = "",
    extraScripts = [];

    // ---------------------------------------------------------------------
    function loadCss(url) {
        var link = document.createElement("link");
        link.type = "text/css";
        link.rel = "stylesheet";
        link.href = url;
        head = document.getElementsByTagName("head")[0];
        head.insertBefore(link, head.childNodes[0]);
    }

    // ---------------------------------------------------------------------
    function loadJavaScript(url) {
        document.write('<script src="' + url + '"></script>');
    }

    // ---------------------------------------------------------------------
    function loadTemplate(url) {
        var templates = document.getElementById("vtk-templates");
        if(templates === null) {
            templates = document.createElement("div");
            templates.setAttribute("style", "display: none;");
            templates.setAttribute("id", "vtk-templates");
            document.getElementsByTagName("body")[0].appendChild(templates);
        }

        // Fetch template and append to vtk-templates
        var request = makeHttpObject();
        request.open("GET", url, true);
        request.send(null);
        request.onreadystatechange = function() {
            if (request.readyState == 4) {
              var content = templates.innerHTML;
              content += request.responseText;
              templates.innerHTML = content;
            }
        };
    }

    // ---------------------------------------------------------------------

    function makeHttpObject() {
        try {
            return new XMLHttpRequest();
        }
        catch (error) {}
        try {
            return new ActiveXObject("Msxml2.XMLHTTP");
        }
        catch (error) {}
        try {
            return new ActiveXObject("Microsoft.XMLHTTP");
        }
        catch (error) {}

        throw new Error("Could not create HTTP request object.");
    }

    // ---------------------------------------------------------------------
    function _endWith(string, end) {
        return string.lastIndexOf(end) === (string.length - end.length);
    }

    // ---------------------------------------------------------------------
    function loadFile(url) {
        if(_endWith(url, ".js")) {
            loadJavaScript(url);
        } else if(_endWith(url, ".css")) {
            loadCss(url);
        } else if(_endWith(url, ".tpl")) {
            loadTemplate(url);
        }
    }

    // ---------------------------------------------------------------------
    // Extract modules to load
    // ---------------------------------------------------------------------
    try {
        modules = script.getAttribute("load").split(",");
        for(var j in modules) {
            modules[j] = modules[j].replace(/^\s+|\s+$/g, ''); // Trim
        }
    } catch(e) {
    // We don't care we will use the default setup
    }

    // ---------------------------------------------------------------------
    // Extract extra script to load
    // ---------------------------------------------------------------------
    try {
        extraScripts = script.getAttribute("extra").split(",");
        for(var j in extraScripts) {
            extraScripts[j] = extraScripts[j].replace(/^\s+|\s+$/g, ''); // Trim
        }
    } catch(e) {
    // We don't care we will use the default setup
    }

    // ---------------------------------------------------------------------
    // If no modules have been defined, just pick the default
    // ---------------------------------------------------------------------
    if(modules.length == 0) {
        //modules = [ "core-min" ];
        modules = [ "core" ];
    }

    // ---------------------------------------------------------------------
    // Extract basePath
    // ---------------------------------------------------------------------
    var lastSlashIndex = script.getAttribute("src").lastIndexOf('lib/core/vtkweb-loader');
    if(lastSlashIndex != -1) {
        basePath = script.getAttribute("src").substr(0, lastSlashIndex);
    }

    // ---------------------------------------------------------------------
    // Add missing libs
    // ---------------------------------------------------------------------
    for(var i in modules) {
        for(var j in vtkWebLibs[modules[i]]) {
            var path = basePath + vtkWebLibs[modules[i]][j];
            loadFile(path);
        }
    }

    // ---------------------------------------------------------------------
    // Add extra libs
    // ---------------------------------------------------------------------
    for(var i in extraScripts) {
        loadFile(extraScripts[i]);
    }

    // ---------------------------------------------------------------------
    // Remove loader
    // ---------------------------------------------------------------------
    script.parentNode.removeChild(script);
}(window));


// ========================================================================
// Constructor
// ========================================================================

PreviewParaview = function (debug) {
	console.debug('PreviewParaview: constructor');
    this.settings = {
        visible: false,
        active: false
    };

    this.volume_xdmf_path = null;
    this.reset_pv_state();
}

PreviewParaview.prototype.reset_pv_state = function() {
    var _this = this;
    var pv_error = $.proxy(function(e){
                    _this.workDone();
                    console.error('PreviewParaview ERROR: ' + e.error);
                }, _this);

    _this.pv_state = {
                stop: vtkWeb.NoOp,
                connectionInfo: null,
                viewport: null,
                pipeline: null,
                proxyEditor: null,
                settingsEditor: null,
                rvSettingsProxyId: null,
                saveOptionsEditor: null,
                defaultSaveFilenames: { 
                                'data': 'server-data/savedData.vtk', 
                                'state': 'server-state/savedState.pvsm', 
                                'screen': 'server-images/savedScreen.png' },
                saveTypesMap: {
                    'AMR Dataset (Deprecated)': 'vtm',
                    'Composite Dataset': 'vtm',
                    'Hierarchical DataSet (Deprecated)': 'vtm',
                    'Image (Uniform Rectilinear Grid) with blanking': 'vti',
                    'Image (Uniform Rectilinear Grid)': 'vti',
                    'Multi-block Dataset': 'vtm',
                    'Multi-group Dataset': 'vtm',
                    'Multi-piece Dataset': 'vtm',
                    'Non-Overlapping AMR Dataset': 'vtm',
                    'Overlapping AMR Dataset': 'vtm',
                    'Point Set': 'vts',
                    'Polygonal Mesh': 'vtp',
                    'Polygonal Mesh': 'vtp',
                    'Rectilinear Grid': 'vtr',
                    'Structured (Curvilinear) Grid': 'vts',
                    'Structured Grid': 'vts',
                    'Table': 'csv',
                    'Unstructured Grid': 'vtu'
                },
                currentSaveType: 'state',
                infoManager: null,
                busyElement: $('.busy').hide(),
                notBusyElement: $('.not-busy').show(),
                busyCount: 0,
                paletteNameList: [],
                pipelineDataModel: { 
                                metadata: null, 
                                source: null, 
                                representation: null, 
                                view: null, 
                                sources: []},
                activeProxyId: 0,
                module: {},
                vcrPlayStatus: false,
                pipelineLoadedCallBack: null,
                error: pv_error
            };

    this.pv_state.module.initializeVisualizer = $.proxy(this.initializeVisualizer, this);
}   

// ========================================================================
// PreviewParaview HTML + CSS management
// ========================================================================

PreviewParaview.prototype.init_html = function() {
    var html_out = '<div class="row-fluid app-wait-start-page">';
    html_out += '<img src="/images/lib/ParaView/Visualizer/start_page_image.png" class="span12 start-page-image">';
    html_out += '<div class="vtk-icon-cog animate-spin start-page-busy-icon"></div>';
    html_out += '</div>';
    html_out += '<div class="pv-pipeline" data-type="pipeline" style="height: 0px; width: 0px; hidden;">';
    html_out += '</div>';                
    html_out += '<div id="fm_preview_paraview_viewport" class="pv-viewport" style="width: 100%; height: 100%;">';                
    html_out += '</div>';                

    $("#fm_preview_paraview").html(html_out);
}

PreviewParaview.prototype.remove_paraview_html = function() {
    $("#fm_preview_paraview").html('');    
}


PreviewParaview.prototype.update_viewport_css = function () {
     // Override default viewport setup
     var width, height;

    $("#fm_preview_paraview_viewport .renderers").css({
        "position": "static", 
        "height": "100%", 
        "width": "100%"});

    var renderers_posistion = $("#fm_preview_paraview_viewport .renderers").position();
    var renders_width = $("#fm_preview_paraview_viewport .renderers").width();
    var renders_height = $("#fm_preview_paraview_viewport .renderers").height();
    

    $("#fm_preview_paraview_viewport .renderers .image").css({
        "top": renderers_posistion.top + "px", 
        "left": renderers_posistion.left + "px", 
        "width": renders_width  + "px",
        "height": renders_height  + "px",
    });

    $("#fm_preview_paraview_viewport .renderers .vgl").css({
        "top": renderers_posistion.top + "px", 
        "left": renderers_posistion.left + "px", 
        "width": renders_width  + "px",
        "height": renders_height  + "px",
    });

    $("#fm_preview_paraview_viewport .renderers .webgl").css({
        "top": renderers_posistion.top + "px", 
        "left": renderers_posistion.left + "px", 
        "width": renders_width  + "px",
        "height": renders_height  + "px",
    });

    $("#fm_preview_paraview_viewport .mouse-listener").css({
        "top": renderers_posistion.top + "px", 
        "left": renderers_posistion.left + "px", 
        "width": renders_width  + "px",
        "height": renders_height  + "px",
    });
    $("#fm_preview_paraview_viewport .statistics").css({
        "top": renderers_posistion.top + "px", 
        "left": renderers_posistion.left + "px", 
        "width": renders_width  + "px",
        "height": renders_height  + "px",
    });
    $("#fm_preview_paraview_viewport .overlay").css({
       "top": renderers_posistion.top + "px", 
        "left": renderers_posistion.left + "px", 
        "width": renders_width  + "px",
        "height": renders_height  + "px",
    });
}

// ========================================================================
// ViewPort management (active + visibility)
// ========================================================================

PreviewParaview.prototype.createViewportView = function(viewportSelector) {
    console.debug('createViewportView');
    /*
    $(viewportSelector).empty()
                       .bind('captured-screenshot-ready', onScreenshotCaptured);
    */
    var session = this.pv_state.session;
    var pv_state = this.pv_state;

    pv_state.viewport = vtkWeb.createViewport({session: session});
    pv_state.viewport.bind(viewportSelector);
    this.update_viewport_css();
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.updateView = function() {
    console.debug('updateView');

    var viewport = this.pv_state.viewport;

    if(viewport) {
        this.update_viewport_css();
        viewport.invalidateScene();
    }
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.resetCamera = function() {
    console.debug('resetCamera');

    var viewport = this.pv_state.viewport;

    if(viewport) {
        this.update_viewport_css();
        viewport.resetCamera();
    }
}

// ========================================================================
// Pipeline management (active + visibility)
// ========================================================================

PreviewParaview.prototype.createPipelineManagerView = function(pipelineSelector) {
    console.debug('createPipelineManagerView');

    var pipeline = $(pipelineSelector);

    var onProxyVisibilityChange = $.proxy(this.onProxyVisibilityChange, this);
    var onPipelineDataChange = $.proxy(this.onPipelineDataChange, this);

    pipeline.pipelineSVG({session: this.pv_state.session});
    pipeline.bind('pipeline-visibility-change', onProxyVisibilityChange);
    pipeline.bind('pipeline-data-change', onPipelineDataChange);
    pipeline.trigger('pipeline-reload');
    this.pv_state.pipeline = pipeline;
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.onProxyVisibilityChange = function(proxy) {
    console.debug('onProxyVisibilityChange');
    this.updateView();
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.onPipelineDataChange = function(event) {
    console.debug('onPipelineDataChange active: ' + event.active);

    var pipelineDataModel = this.pv_state.pipelineDataModel;
    var proxyEditor = this.pv_state.proxyEditor;
    // { active: active_proxy_id, view: view_id, sources: proxy_list }

    this.pv_state.activeProxyId = event.active;

    // Update data model

    pipelineDataModel.sources = event.sources;

    // Handle the new active proxy
    if(event.active === '0') {
        $('.need-input-source').hide();
        proxyEditor.empty();
        this.updateView();
    } else {
        $('.need-input-source').show();
        pipelineDataModel.metadata = this.getProxyMetaData(event.active);
        pipelineDataModel.source = null;
        pipelineDataModel.representation = null;
        if(pipelineDataModel.metadata) {
            this.loadProxy(pipelineDataModel.metadata.id, 'source');
            this.loadProxy(pipelineDataModel.metadata.rep, 'representation');
            if(pipelineDataModel.view === null) {
                console.debug('onPipelineDataChange - > loadProxy');
                this.loadProxy(event.view, 'view');
            }
        }
    }
}

// ========================================================================
// Proxy Editor management (update + delete)
// ========================================================================

PreviewParaview.prototype.createProxyEditorView = function(proxyEditorSelector) {
    console.debug('createProxyEditorView');
    this.pv_state.proxyEditor = $(proxyEditorSelector);
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.onProxyApply = function(event) {
    var _this = this;
    var session = _this.pv_state.session;

    console.debug('onProxyApply');

    _this.startWorking();
    var invalidatePipeline = $.proxy(_this.invalidatePipeline, _this);

    session.call('pv.proxy.manager.update', [event.properties]).then(invalidatePipeline, invalidatePipeline);
    
    // Args: representation, colorMode, arrayLocation='POINTS', arrayName='', vectorMode='Magnitude', vectorComponent = 0, rescale=False
    var args = [].concat(event.colorBy.representation, event.colorBy.mode, event.colorBy.array, event.colorBy.component);
    this.startWorking();
    session.call('pv.color.manager.color.by', args).then(this.invalidatePipeline, this.pv_state.error);
    // Update palette ?
    if(event.colorBy.palette) {
        this.startWorking();
        session.call('pv.color.manager.select.preset', [ event.colorBy.representation, event.colorBy.palette ]).then(invalidatePipeline, this.pv_state.error);
    }
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.onRescaleTransferFunction = function(event) {
    console.debug('onRescaleTransferFunction');

    var _this = this;
    var proxyEditor = _this.pv_state.proxyEditor;
    var viewPort = _this.pv_state.viewPort;
    var session = _this.pv_state.session;

    console.debug('onRescaleTransferFunction');
    console.debug('onRescaleTransferFunction: ' + Object.keys(event));
    console.debug('onRescaleTransferFunction => event.id: ' + event.id);
    console.debug('onRescaleTransferFunction => type: ' + event.type + ', typeof: ' + typeof(event.type));
    console.debug('onRescaleTransferFunction => mode: ' + event.mode + ', typeof: ' + typeof(event.mode));

    _this.startWorking();
    var options = { proxyId: event.id, type: event.mode };
    if(event.mode === 'custom') {
        options.min = event.min;
        options.max = event.max;
    }
    console.debug('onRescaleTransferFunction options.proxyId: ' + options.proxyId);
    console.debug('onRescaleTransferFunction options.type: ' + options.type);
    console.debug('onRescaleTransferFunction options.min: ' + options.min);
    console.debug('onRescaleTransferFunction options.max: ' + options.max);
    
    session.call('pv.color.manager.rescale.transfer.function', [options]).then(function(arg) {
        if (arg['success'] === true) {
            _this.pv_state.viewPort.invalidateScene();
            proxyEditor.trigger({
                'type': 'update-scalar-range-values',
                'min': successResult.range.min,
                'max': successResult.range.max
            });
            session.call('pv.color.manager.rgb.points.get', [event.colorBy.array[1]]).then(function(result) {
                proxyEditor.trigger({
                    'type': 'notify-new-rgb-points-received',
                    'rgbpoints': result
                });
                _this.workDone();
            }, _this.pv_state.error);
        } else {
            _this.workDone();
        }
    }, _this.pv_state.error);
    
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.onNewProxyLoaded = function() {
    //console.debug('onNewProxyLoaded');
    var pipelineDataModel = this.pv_state.pipelineDataModel;
    var proxyEditor = this.pv_state.proxyEditor;
    var paletteNameList = this.pv_state.paletteNameList;
    //console.debug('onNewProxyLoaded metadata keys: ' + Object.keys(pipelineDataModel['metadata']));
    console.debug('onNewProxyLoaded id: ' + pipelineDataModel['metadata']['id'] + 
                  ', name: ' + pipelineDataModel['metadata']['name'] + 
                  ', rep: ' + pipelineDataModel['metadata']['rep']);
    
    if(pipelineDataModel.metadata && pipelineDataModel.source && pipelineDataModel.representation && pipelineDataModel.view) {
        var colorBy = pipelineDataModel.representation.colorBy,
            props = [],
            ui = [],
            options = {};

        try {
            proxyEditor.proxyEditor(pipelineDataModel.metadata.name,
                                    pipelineDataModel.metadata.leaf,
                                    pipelineDataModel.metadata.id,
                                    props,
                                    ui,
                                    pipelineDataModel.source.data.arrays,
                                    paletteNameList,
                                    colorBy,
                                    options);
        } catch(err) {
            console.log(err);
        }

        // Handle callback if any
        if(this.pv_state.pipelineLoadedCallBack) {
            this.pv_state.pipelineLoadedCallBack();
            this.pv_state.pipelineLoadedCallBack = null;
        }

        // Handle automatic reset camera
        if(pipelineDataModel.sources.length === 1) {
            this.resetCamera();
        } else {
            this.updateView();
        }
    }
}


// ========================================================================
// Main - Visualizer Setup
// ========================================================================

PreviewParaview.prototype.initializeVisualizer = function(viewportSelector, 
                                                  pipelineSelector, 
                                                  proxyEditorSelector) {
    console.debug('initializeVisualizer');

    // Create panels

    this.createViewportView(viewportSelector);
    this.createPipelineManagerView(pipelineSelector);
    this.createProxyEditorView(proxyEditorSelector);

    // Set initial state

    this.pv_state.proxyEditor.empty();
}

// ========================================================================
// Main callback
// ========================================================================

PreviewParaview.prototype.invalidatePipeline = function(arg) {
    console.debug('invalidatePipeline');

    var pv_state = this.pv_state;

    if(arg && arg.hasOwnProperty('id')) {
        // Update active proxy in pipeline
        this.activeProxy(arg.id);
    }
    pv_state.pipeline.trigger('pipeline-reload');
    pv_state.viewport.resetViewId();
    pv_state.viewport.invalidateScene();
    this.workDone();
}


// ========================================================================
// Busy feedback
// ========================================================================

PreviewParaview.prototype.startWorking = function() {
    this.pv_state.busyCount++;
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.workDone = function() {
    this.pv_state.busyCount--;
}

// ========================================================================
// Helper methods
// ========================================================================

PreviewParaview.prototype.activeProxy = function(newActiveProxy) {
    console.debug('activeProxy: ' + newActiveProxy);
    if(newActiveProxy) {
        this.pv_state.pipeline.data('pipeline').active_proxy = newActiveProxy;
    }
    return this.pv_state.pipeline.data('pipeline').active_proxy;
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.getProxyMetaData = function(id) {
    console.debug('getProxyMetaData: ' + id);
    
    var pipelineDataModel = this.pv_state.pipelineDataModel;
    var list = pipelineDataModel.sources,
        count = list.length;

    while(count--) {
        if(list[count].id === id) {
            return list[count];
        }
    }
    return null;
}

// ------------------------------------------------------------------------

PreviewParaview.prototype.loadProxy = function(proxy_id, name) {
    console.debug('loadProxy -> id: ' + proxy_id + ', name: ' + name);
    var _this = this;
    var pipelineDataModel = _this.pv_state.pipelineDataModel;
    var session = _this.pv_state.session;
    if(session) {
        _this.startWorking();
        session.call("pv.proxy.manager.get", [proxy_id]).then(
            function(proxy){
                _this.workDone();
                pipelineDataModel[name] = proxy;
                console.debug('loadProxy -> onNewProxyLoaded: ' + proxy);
                _this.onNewProxyLoaded();
            }, _this.pv_state.error);
    }
}

// ========================================================================
// IDMC methods
// ========================================================================

PreviewParaview.prototype.set_volume_xdmf = function(volume_xdmf_filepath) {
    this.volume_xdmf_filepath = './' + volume_xdmf_filepath;
    console.debug('set_volume_xdmf: volume_xdmf_filepath: ' + this.volume_xdmf_filepath);
}

PreviewParaview.prototype.start_rendering = function() {
    console.debug('PreviewParaview.start_rendering')
    this.render_volume_xdmf();
}

PreviewParaview.prototype.render_volume_xdmf = function() {
    var _this = this;
    var fullpathFileList = _this.volume_xdmf_filepath;
    var session = _this.pv_state.session;

    console.debug('PreviewParaview.render_volume_xdmf: ' + fullpathFileList);

    session.call("pv.proxy.manager.create.reader", [fullpathFileList]).then(    
        function(arg) {
            console.debug('pv.proxy.manager.create.reader: ' + arg.id);
            _this.pv_state.pipelineLoadedCallBack = function(arg) {
                console.debug('pipelineLoadedCallBack');
                
                var pipelineDataModel = _this.pv_state.pipelineDataModel;

                var metadata = pipelineDataModel.metadata;
                var src_props = pipelineDataModel.source.properties;
                var view_props = pipelineDataModel.view.properties;
                var repr_props = pipelineDataModel.representation.properties;

                // Set source properties

                var src_count = src_props.length;
                var prop;
                var idx;
                var volume_name;
                var new_props = [];
                
                
                for(idx = 0; idx < src_count; ++idx) {
                    prop = src_props[idx];
                    
                    if (prop.name === 'PointArrayStatus') {
                        volume_name = prop.value;
                        
                    }
                    if (prop.name === 'GridStatus' && prop.value == '') {
                        // For some reason (reusing an empty GridStatus fails)
                        console.debug('skipping empty property: ' + prop.name);
                    }
                    else {
                        new_props.push(prop);    
                    }
                                    }

                // Set representation properties

                var repr_count = repr_props.length;

                for(idx = 0; idx < repr_count; ++idx) {
                    prop = repr_props[idx];

                    if (prop.name === 'Representation') {
                        prop.value = 'Volume';
                    }
                    
                    new_props.push(prop);
                }
                
                var view_count = view_props.length;

                for(idx = 0; idx < view_count; ++idx) {
                    prop = view_props[idx];
                    new_props.push(prop);
                }
                    
                
                // Set color palette

                var colorBy = pipelineDataModel.representation.colorBy;

                colorBy.palette = 'X Ray';
                colorBy.mode = 'ARRAY';
                colorBy.array [1] = new String(volume_name);
                colorBy.array[2] = '';

                
                _this.onProxyApply({
                    colorBy: colorBy,
                    properties: new_props
                });
                
            };
            _this.invalidatePipeline(arg); 
        }, _this.pv_state.error);
}

PreviewParaview.prototype.open = function() {
    console.debug('PreviewParaview.launch: ' + Object.keys(this));
    var _this = this;

    // Start with fresh pv_State
    _this.reset_pv_state();

    var pv_state = this.pv_state;
    var pv = pv_state.module;
    var start_rendering = $.proxy(this.start_rendering, this);

    var config = {
            sessionManagerURL: vtkWeb.properties.sessionManagerURL,
            application: "visualizer"
        },
        start = function(connectionInfo) {
            console.debug('PreviewParaview launch start');
            
            $(".app-wait-start-page").css("visibility", 'hidden');
            $(".app-wait-start-page").css("height", '0%');

            pv_state.connectionInfo = connectionInfo;
            pv_state.session = connectionInfo.session;
            
            pv_state.module.initializeVisualizer(
                ".pv-viewport", 
                ".pv-pipeline",
                ".pv-proxy-editor"
                );            
            start_rendering();
        };

    // Try to launch the Viz process

    this.init_html();

    console.debug('PreviewParaview launch url: ' + config.sessionManagerURL);
    vtkWeb.smartConnect(config, start, function(code,reason){
        console.debug('PreviewParaview connectionInfo closed, code: ' + ', reason: ' + reason);
    });
}

PreviewParaview.prototype.close = function() {
    var _this = this;
    var pv_state = this.pv_state;
    var session = pv_state.session;
    var connectionInfo = pv_state.connectionInfo;
    console.debug('closing paraview');

    try {
        console.debug('calling application.exit');
        session.call("application.exit", []);
        connectionInfo.connection.close();

    } catch(exception) {
        console.debug('PreviewParaview.close exception: ' + exception);
    }
    
    _this.reset_pv_state();
    _this.remove_paraview_html();
    console.debug('stopped paraview');
}

PreviewParaview.prototype.refresh = function(visible, callback) {
    console.debug('paraview refresh: visible: ' + visible);
    console.debug('paraview refresh: callback: ' + callback);
    console.debug('paraview refresh: this.settings.visible : ' + this.settings.visible);
    //this.debug_js_object(this);
    if (this.settings.visible == true && visible == false) {
        this.close();
        console.debug('paraview refresh -> close');
    }
    else if (this.settings.visible == false && visible == true) {
        this.open();
        console.debug('paraview refresh -> open');
    }
    else if (this.settings.visible == true && visible == true) {
        this.updateView();
        console.debug('paraview refresh -> update');
    }

    this.settings.visible = visible;

    if (typeof callback === "function") {
        callback();
    }
}