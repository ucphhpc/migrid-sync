def generate_name():
    timestamp = generate_timestamp()
    return timestamp+".mRSL"

def generate_folder_name():
    timestamp = generate_timestamp()
    return timestamp

def generate_timestamp():
    import time
    (y,mo,d,h,m,s,_,_,_)= time.localtime()
    timestamp = "%i_%i_%i_%i_%i_%i" % (h,m,s,d,mo,y)
    return timestamp



def time_diff(t0, t1):
    import time
    #t1 = time.strptime("Finished: Tue Apr 29 08:28:48 2008","Finished: %a %b %d %H:%M:%S %Y")
    #t2 = time.strptime("Finished: Tue Apr 29 08:35:46 2008","Finished: %a %b %d %H:%M:%S %Y")
    diff = time.mktime(t1) - time.mktime(t0)
    elapsed = "%d min %d secs"% (int(diff)/60, int(diff)%60)
    return int(diff), elapsed

"""
#
t1 = time.time()
#
res = func(*arg)
#
t2 = time.time()
#
print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
#
return res
"""
