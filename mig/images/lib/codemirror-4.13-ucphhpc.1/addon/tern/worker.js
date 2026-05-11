// CodeMirror, copyright (c) by Marijn Haverbeke and others
// Distributed under an MIT license: http://codemirror.net/LICENSE

// declare global: tern, server

var server;

this.onmessage = function(e) {
  var data = e.data;
  switch (data.type) {
  case "init": return startServer(data.defs, data.plugins, data.scripts);
  case "add": return server.addFile(data.name, data.text);
  case "del": return server.delFile(data.name);
  case "req": return server.request(data.body, function(err, reqData) {
    postMessage({id: data.id, body: reqData, err: err && String(err)});
  });
  case "getFile":
    // IMPORTANT: make sure user-controlled data is used very carefully
    var id = data.id;
    if (typeof id == "number" && isFinite(id) && Math.floor(id) === id && id > 0 &&
        Object.prototype.hasOwnProperty.call(pending, id)) {
      var c = pending[id];
      delete pending[id];
      if (typeof c == "function") {
        return c(data.err, data.text);
      }
    }
    return;
  default: throw new Error("Unknown message type: " + data.type);
  }
};

var nextId = 0, pending = {};
function getFile(file, c) {
  postMessage({type: "getFile", name: file, id: ++nextId});
  pending[nextId] = c;
}

function startServer(defs, plugins, scripts) {
  if (scripts) importScripts.apply(null, scripts);

  server = new tern.Server({
    getFile: getFile,
    async: true,
    defs: defs,
    plugins: plugins
  });
}

var console = {
  log: function(v) { postMessage({type: "debug", message: v}); }
};
