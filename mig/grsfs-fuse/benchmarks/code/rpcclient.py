import xmlrpclib,timeit

setup = """import xmlrpclib; proxy = xmlrpclib.ServerProxy("http://n7:8000/")"""
print timeit.repeat("proxy.x()", setup = setup, repeat=3, number=1000)
