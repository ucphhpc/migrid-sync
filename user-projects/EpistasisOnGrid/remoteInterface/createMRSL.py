from timestamp import generateName

def generateDockingMRSL(mvdScript, moleculeFiles, jobDir, resourceSpecsDict={}, notifyEmail=""):

    staticInputFiles = [
    "MVD/misc/data/ElementTable.csv",
    "MVD/misc/data/PreparationTemplate.xml",
    "MVD/misc/data/Residues.txt",
    "MVD/misc/data/RerankingCoefficients.txt",
    "MVD/misc/data/sp3sp3a.csv",
    "MVD/misc/data/sp2sp2a.csv",
    "MVD/misc/data/sp2sp3a.csv",
    "MVD/misc/data/bindinAffinity.mdm",
    "MVD/bin/vinter.license"]

    # loose the ".mvdscript", add ".tar"
    outputFile = "output_"+mvdScript[:-10]+".tar" 

    executeMvdCommand = "MVD/bin/mvd "+mvdScript+ " -nogui"

    mrsl = []
    mrsl.append("::EXECUTE::\n")
    mrsl.append("chmod 755 MVD/bin/mvd \n")
    mrsl.append(executeMvdCommand+"\n")
    #mrsl.append("cd MVD/bin \n")
    mrsl.append("tar -cf "+outputFile+" *.*\n")
	      #+ "--exclude vinter.license target.mvdml *.mvdscript compounds.mol2 \n")

    if notifyEmail != "":
       mrsl.append("\n::NOTIFY::\n")
       mrsl.append(notifyEmail+"\n")

    mrsl.append("\n::INPUTFILES::"+"\n")
    for path in staticInputFiles:
	mrsl.append(path+"\n")

    for file in moleculeFiles:
	mrsl.append(file+"\n")

    mrsl.append("\n::OUTPUTFILES::"+"\n")

    mrsl.append(outputFile+"\n")

    mrsl.append("\n::EXECUTABLES::\n")
    mrsl.append("MVD/bin/mvd \n")

    if resourceSpecsDict.has_key("mem"):
	mrsl.append("\n::MEMORY::\n")
	mrsl.append(resourceSpecsDict["mem"]+"\n")

    if resourceSpecsDict.has_key("disc"):
	mrsl.append("\n::DISK::\n")
	mrsl.append(resourceSpecsDict["disc"]+"\n")

    if resourceSpecsDict.has_key("CPUtime"):
	mrsl.append("\n::CPUTIME::\n")
	mrsl.append(resourceSpecsDict["CPUtime"]+"\n")               

    #print string.join(mrsl)
    mrslName = "mig_"+mvdScript[:-10]+".mRSL"
    mrslFile = open(jobDir+"/"+mrslName, "w")
    mrslFile.writelines(mrsl)
    mrslFile.close()
    return mrslName


def generateMRSL(exeCommands, inputfiles, outputfiles, dest, executables=[], resourceSpecsDict={}, notifyEmail="", runtenv="", mem=100, disc=10, CPUtime=10, vgrid="Generic"):

    mrsl = []
    mrsl.append("::EXECUTE::\n")
    for cmd in exeCommands:
        mrsl.append(cmd+"\n")        
#    mrsl.append("tar -cf "+outputfile+" *.*\n")
	      #+ "--exclude vinter.license target.mvdml *.mvdscript compounds.mol2 \n")

    if notifyEmail != "":
       mrsl.append("\n::NOTIFY::\n")
       mrsl.append(notifyEmail+"\n")

    mrsl.append("\n::INPUTFILES::"+"\n")
    for path in inputfiles:
	mrsl.append(path+"\n")

    mrsl.append("\n::OUTPUTFILES::"+"\n")
    for f in outputfiles:
	mrsl.append(f+"\n")

    mrsl.append("\n::EXECUTABLES::"+"\n")
    for f in executables:
        mrsl.append(f+"\n")
    
    mrsl.append("\n::MEMORY::\n")
    mrsl.append(str(mem)+"\n")

    mrsl.append("\n::DISK::\n")
    mrsl.append(str(disc)+"\n")

    mrsl.append("\n::CPUTIME::\n")
    mrsl.append(str(CPUtime)+"\n")               
        


    for label, value in resourceSpecsDict.iteritems():
        mrsl.append("\n::"+label+"::\n")
        mrsl.append(value+"\n")
        
    
    mrsl.append("\n::RUNTIMEENVIRONMENT::\n")                   
    mrsl.append(runtenv+"\n")

    mrsl.append("\n::VGRID::\n")
    mrsl.append(vgrid+"\n")     

    mrslname = generateName()
    mrslpath = dest+mrslname
    mrslFile = open(mrslpath, "w")
    mrslFile.writelines(mrsl)
    mrslFile.close()
    return mrslpath

