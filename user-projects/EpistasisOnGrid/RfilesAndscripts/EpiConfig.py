# run locally or on MiG
executionMode = "mig" #"local" 
mainScript = "EpiScript.py"
pollFrequency = 5


inputFiles = ["EpiCRnew_R_edit.R","DistrPost07_R_edit.R", "EpiPS_R_edit.R", "HWEwigNew_R_edit.R"]
programFiles =  ["EpiMain.R", "EpiCRnew_R_edit.R","DistrPost07_R_edit.R", "EpiPS_R_edit.R", "HWEwigNew_R_edit.R", "Inter99All290606.sav", "EpiConfig.py"]
 #,"EpiScript.py"]

geneFirstIndex = 74 #74
geneLastIndex = 75 #103

traitFirstIndex = 36 #7
traitLastIndex = 37 #37
selectionVariableIndex = 2
selectionVariableName = "Gender"
dataFile = "Inter99All290606.sav"
EpiProgramPath = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/epistatis/Epistasis/" 
EpiWorkingDir = "MiGepistasis/"
if executionMode == "local":
    EpiWorkingDir = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/fakeMiGDir/"+EpiWorkingDir
outputDir = "epifiles/"
preMiGDir = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/fakeMiGDir/MiGepistasis/"
jobSize = 2

initJob = {}
initJob["geneIndex1"] = geneFirstIndex
initJob["geneIndex2"] = geneLastIndex
initJob["traitIndex1"] = traitFirstIndex
initJob["traitIndex2"] = traitLastIndex
initJob["programFiles"] = programFiles
initJob["inputFiles"] = inputFiles
initJob["mainScript"] = mainScript 
initJob["selectionVariable"] = selectionVariableIndex
initJob["selectionVariableName"] = selectionVariableName
initJob["dataFile"] = dataFile
initJob["path"] = EpiProgramPath
initJob["selVarValues"] = [1,2] # for gender
initJob["workingDir"] = EpiWorkingDir
initJob["outputDir"] = outputDir
