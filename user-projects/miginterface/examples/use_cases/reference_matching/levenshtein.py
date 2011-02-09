import sys, re, time, imp, os

(kernel,user,kernvers,t,machine) = os.uname()
if machine != "x86_64":
     imp.load_dynamic('Levenshtein', 'Levenshtein_i686.so')
else:
    if sys.maxunicode > 65535: # use different builds based on whether the host system has python unicode 2 or 4 
        imp.load_dynamic('Levenshtein', 'Levenshtein_ucs4.so')
    else:
        imp.load_dynamic('Levenshtein', 'Levenshtein_ucs2.so')
 
from Levenshtein import distance

# Function for calculating the normalized edit distance.
def normalize_edit_distance( string1, string2, edit_distance ):
    
    # First determine the length of the longest string. 
    l1 = len(string1)
    l2 = len(string2)

    max_length = float(l1);
    if l2 > l1:
        max_length = float(l2);
        
    # Then calculate and return the normalized edit distance.
    return "%.4f" %( 1.0 - (edit_distance / max_length) );


def edit_distance(ref_file):
    #t1 = time.time()
    # old : Parse the input list of strings to gather the IDs in an array.
    id_dict = {}
    ref_list = []

    f = open(ref_file, "r")
    for line in f:
        # old: Parse the line, and extract the ID and string.
        line = line.strip()
        divider = line.find(" ")
        id = line[0:divider]
        ref = line[divider+1:]
        ref = re.sub('[^a-z0-9 ]', '', ref.strip().lower(),)
        # old: Store string in dictionary (though only if it is one of the pairs we compare!).
        #ref_list = []
        if not id_dict.has_key(id):
            id_dict[id] = 1
            ref_list.append((id,ref))    
    
    
    size = len(ref_list)
    i = 0
    #unit_count = 0 # pair counter
    while i < size:
        j = i+1
        while j < size:
            pair = (ref_list[i],ref_list[j]) # (i,j)
            ref1 = pair[0] # first reference (id, text) in pair
            ref2 = pair[1] # second reference (id, text) in pair
            ref1id = ref1[0] # reference id
            ref1str = ref1[1] # reference text
            ref2id = ref2[0] # reference id
            ref2str = ref2[1] # reference text
            edit_distance = distance(ref1str, ref2str)
            norm_edit_distance = normalize_edit_distance(ref1str, ref2str, edit_distance)
            print ref1id, ref2id, edit_distance, norm_edit_distance;
            j+=1
        i+=1


if __name__=="__main__":
    if len(sys.argv) != 2:
        print "Takes reference file as input"
        sys.exit()
    data = sys.argv[1]
    edit_distance(data)
