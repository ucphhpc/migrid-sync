# run locally or on MiG
executionMode = "mig" #"local" 
mainScript = "RfilesAndscripts/EpiMiGExec.py"
pollFrequency = 5

inputFiles = ["EpiCRnew_R_edit.R","DistrPost07_R_edit.R", "EpiPS_R_edit.R", "HWEwigNew_R_edit.R"]
#programFiles =  ["EpiMain.R", "EpiCRnew_R_edit.R","DistrPost07_R_edit.R", "EpiPS_R_edit.R", "HWEwigNew_R_edit.R", "Inter99All290606.sav", "EpiConfigUS.py", mainScript]

Rfiles = ["RfilesAndscripts/EpiMain.R", "RfilesAndscripts/EpiCRnew_R_edit.R","RfilesAndscripts/DistrPost07_R_edit.R", "RfilesAndscripts/EpiPS_R_edit.R", "RfilesAndscripts/HWEwigNew_R_edit.R"]
dataFile = "RfilesAndscripts/Inter99All290606.sav"

programFiles = ["RfilesAndscripts/EpiMain.R", "RfilesAndscripts/EpiCRnew_R_edit.R","RfilesAndscripts/DistrPost07_R_edit.R", "RfilesAndscripts/EpiPS_R_edit.R", "RfilesAndscripts/HWEwigNew_R_edit.R",dataFile, "Configuration/EpiConfigUS.py", mainScript]


#programFiles =  Rfiles.extend(["EpiConfigUS.py",mainScript])
#files = program[]

geneFirstIndex = 74 #74
geneLastIndex = 75 #103

traitFirstIndex = 7 #7
traitLastIndex = 8 #37
selectionVariableIndex = 2
#selectionVariableName = "Gender"
#selectionVariableValues = [1,2]

#selectionVariableIndex = 5
#selectionVariableName = "FINSLCA1"
#selectionVariableValues = range(1,20) # 19 classes


EpiProgramPath = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/epistatis/Epistasis/" 
#EpiWorkingDir = "MiGepistasis/"
EpiWorkingDir = "tmp/"
if executionMode == "local":
    EpiWorkingDir = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/fakeMiGDir/"+EpiWorkingDir
outputDir = "epifiles/"
preMiGDir = "/home/benjamin/Dokumenter/CSPBuilder/myCSPBuilderPrj/fakeMiGDir/MiGepistasis/"

#jobSize = 1
#vgrid = "DIKU"
vgrid= "DCSC"
#resourceSpecs = {"ARCHITECTURE":"AMD64"}
resourceSpecs = {"RUNTIMEENVIRONMENT": "GNU_R"}
defaultUserOutputDir = "epifiles/"

valuesDict = {'2':[1,2], '5':range(1,20)}
#jobSize = -7
resultsdirPrefixName = "EpistasisFiles"
