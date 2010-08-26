import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer

def x():
        return True

server = SimpleXMLRPCServer(('', 8000))
print "Listening on port 8000..."
server.register_function(x, "x")
server.serve_forever()
