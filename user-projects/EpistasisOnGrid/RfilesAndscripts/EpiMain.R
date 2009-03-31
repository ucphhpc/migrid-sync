#Epistatis: this is the working script!!!

#UDVIKLING I den menustyrede version bør genotyperne klassificeres som AA, Aa og aa, således at programmet kan identificere homozygote
#og heterozygote. Kun re-klassificerede gener kan testes, og i øvrigt skal det være muligt at vælge hvilke gener der skal indgå i
#undersøgelserne. Ligeledes skal traits også kunne vælges frit, og ikke som nu være afhængig af en samlet liste.
#De traits sm testes for significans anføres p-value.
#Drop single-gene var her og brug Falconer fra Heritability
#Kan det være rigtigt at LD ikke kan beregnes hvis hvert gen kun har to genotyper?
#NBNB F-test has min p-value of 1.1e-16. Upto e-14 it is heavely rounded. Thats in S6.2. what about S7.0 and byond??64BIT??
#OUTputtet til videre behandling (se working files) skal ændres til en blok hvor al tekst er på engelsk!!

"convertToInt"<-function(stringlist)
{
 
  if(is.integer(as.integer(stringlist[1]))){
    new = T
    newlist = seq(length=length(stringlist),from=0, to=0)
    for(s in 1:length(newlist)){
      newlist[s] = as.integer(stringlist[s])
      print (newlist[s])
    }
    newlist
  }else{
      stringlist
  }
}

"writeToFile"<-function(data,filename)
{
#  print(paste("Writing to file ",filename))
write.table(data, filename, sep="\t", append=T, quote=F, col.names=F, row.names=F)
}

"RunEpistasisForClass" <- function(valueRange, smplt, selVar, genelist, traitnamelist)
{
hnames<-names(smplt)
#Ovenstående udksriver headings fra basis-filen, men bruges vist kun til valg af classificationsvar

#Choose selection variable
selectvar<<-selVar #2
#Name selectionvariabel
nselvar<<-hnames[selVar]#selName#"Gender"

#Select gene1
#genenr1 = geneIndex1#74
#Select gene2
#genenr2 = geneIndex2#103

#First trait
#trait1<<-traitIndex1#7
#Last trait
#trait2<<-traitIndex2#37
traits <<- traitnamelist
genes <- genelist
#SIGNIFICANCE LEVELS
#Signifcans level for epistasis
epistsign<<-0.05#SKAL DENNE VÆRE GLOBAL???????BRUGES JO KUN I STARTEN NEDENFOR

#CORRECTION FOR MULITPLE TESTING
#Shall Bonferoni correction be used in selection of trait-summary?: ("T" = yes, everything else is no)
boncorT<-"T"


#Maybe we should use the same characters for missing values
#Missing values to be excluded for genes
misv = "?"
#Missing values to be excluded for traits
misvt<<- -99

#File extensions
#Epistasis and heritabilities summary
hepiexts<<-".txt"
#Logile
logext<<-".txt"
################DONT WRITE ANYTHING BELOW THIS LINE#############################

#Number of classes
levmax<<-max(smplt[c(selectvar)],na.rm=T)

#Bonferoni corrections for genes
#benja edit: gene indexes no longer present
#numgene<<-abs(genenr2-genenr1)+1
numgene <<-length(genes)
numtest<-numgene*(numgene-1)/2

#Bonferoni corrections for epistasis
#benja edit: trait indexes no longer present
#numtr<-abs(as.numeric(trait2)-as.numeric(trait1)+1)
numtr<-length(traits)
if(boncorT=="T")
	{epistsign<<-epistsign/(numtest*levmax*numtr)} else{epistsign==epistsign}

#Váriables for output and works also as counters
totaltest<-numtest
totaltest2<-numtest*numtr

#Logfile for progression of calcluations
logsave<-paste("Log progress of Epistasis") 

logtitel<-matrix(c("EPISTASIS LOGFILE"),nrow=1)
studyfile<-matrix(c("File:","","",fileimp),nrow=1)
studyvar<-matrix(c("Classification variable:","",names(smplt[c(selectvar)])),nrow=1)
studyclass<-matrix(c("Nymber of clases:","",levmax),nrow=1)
studygenes<-matrix(c("Number of genes:","",numgene),nrow=1)
studytraits<-matrix(c("Number of traits:","",numtr),nrow=1)
tablehead<-matrix(c("Test number","","Class","Time"),nrow=1)

writeToFile(logtitel,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(date(),paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(studyfile,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(studyvar,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(studyclass,paste(logsave,logext,sep=""))
writeToFile(studygenes,paste(logsave,logext,sep=""))
writeToFile(studytraits,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(tablehead,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))


####


#Run calculations for all classes...
tblnum<<-0#to avoid headings for every class
lognum<<-0#to avoid headings in log-files. NB different loop than tblnum
calcno<<-0#counts number of actual calculated tests


#Counters
testno<-1
teststart<-1
calcsign<-0

#Start test of one class at a time
#for(lev in 1:levmax) {
# edit : Only execute a selected range 
for(lev in valueRange) {
	sval<<-lev
#if(sval>levmax || sval<1)stop("Levels out of bounce")
	tfilt <- paste(names(smplt[c(selectvar)]), "=", sval)
        
	# importer alle rækker med pågældende filter ("gender = 1")
	#Redit: smpl <- importData(file=fileimp, filter = tfilt)
	#selectvec <- smplt[,c(selectvar)]==sval # lav en logical vector over filtret
        selectvec <- smplt[,selectvar]==sval 
        #boolist <- smplt[,"GENDER"]==1
	#smpl <- read.spss(file=fileimp)
        smpl<<-smplt[selectvec,] # lav ny dataframe med udvalgte rækker (note: efterfølgende ',' )
        svarn <- names(smpl[selectvar])
      
# benja edit: gene indexes are no longer used        
#if (genenr1==genenr2){
#    stop ("No range of genes has been selected")}
#	else {if (genenr1>genenr2)
#		     {gene1r<-genenr2
 #			  gene2r<-genenr1}
#			  else
#			 {gene1r<-genenr1
# 			  gene2r<-genenr2}
 #}#end if(sval>levmax ....

if (length(genes)<2){
stop ("No range of genes has been selected")
}
###

#Start test of all gene-combinations in thje selected class.

for(gene1 in genes){
  for(gene2 in genes[length(genes):0]){ # loop through the genes in reverse order
    if(gene1 == gene2){
      break
    }

  gname1<<- names(smplt[c(gene1)])
  gname2<<- names(smplt[c(gene2)])
    
# benja edit: gene indexes are no longer used. Instead a list of gene names are in the "genes" vector 
#while(gene1r <gene2r) {
#repeat{	
#  gname1<<-names(smplt[c(gene1r)])
#  gname2<<-names(smplt[c(gene2r)])
  
  # alle gname1 og gname2 gener for en klasse(GENDER) 

  # Redit : geneVector1 <- factor(as.character(smpl[, c(gname1)]), exclude=misv)
  # alternate: geneVector1 <- factor(as.character(smpl[c(gname1)]), exclude=misv)
  # blank spaces must be removed (gsub) in order for "exclude" to match "?"
  # benja note: "factor" gør at geneVector1-2 kun indeholder 1 level for hver gen værdi
  geneVector1 <<- factor(gsub(" ", "",as.character(smpl[, c(gname1)])), exclude=misv)
  geneVector2 <<- factor(gsub(" ", "",as.character(smpl[, c(gname2)])), exclude=misv)
 
  crosst<-table(geneVector1,geneVector2)

#This cross tab is used to skip monomorphic genes.
#NB the dim-function works fine here, but not in DistrPost. Thats the reaosn for
#the extended test in DistrPost, but it shoul not be so. The problem is that the genotype list
#is from this script and not from the trimmed script in Distr..
#Maybe you did solve this problem in DistrPost, Benjamin??
#Anyhow, can union-function be used in C, C++ etc?

#Test if monomorphic genes. If so, the gene is skiped
if(dim(crosst)[1]<2){firstacc=0}
	else{firstacc=1}
if(dim(crosst)[2]<2){secondacc=0}
	else{secondacc=1}
	matacc<-firstacc+secondacc
if(matacc<2){
    action<-"Skip"
	testno<-testno+1
	#gene2r <- gene2r - 1	#andet gen vælges bagfra
             # gene indexes are no longer used
    next
	}
else{

####
     #AND NOW CALCULATIONS!
  calcnum<-DistrPost()
  lognum<<-lognum+1
  calcsign<-calcsign + calcnum
}
#signtraits bruges ikke pt(DistrPost kaldes dog!!)

   updatescreen<-c(testno,"of",totaltest,sval,date(),sep="")
#Redit: print(c("Test No:",updatescreen)) # udskrifter

 # Redit: added flags for printing format
  writeToFile(matrix(updatescreen,nrow=1),paste(logsave,logext,sep=""))
print(updatescreen)

#  print(paste("new gene2: ",gene2r))
   # print(paste("new gene2: ",gname2))
    
#  if(gene2r==gene1r) 
#    break
  
}# end repeat statement
#gene2r<-geneend
#gene1r<-gene1r+1
#print(paste("new gene1: ",gene1r))
#print(paste("new gene1: ",gname1))
}# end calculations for all gene combinations in one class.

   tblnum<-tblnum+1
   #used to avoid printing of headings all the time. Does not work properly after remodelling.

 }#end calculations for all classes...

numcalc<-matrix(c("Number of test actually calculated:",calcsign,"ofnumber of tests:",totaltest2),nrow=1)
endcalc<-matrix(c("End of calculations:",date()),nrow=1)

# Redit : added flags for printing format
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(numcalc,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(endcalc,paste(logsave,logext,sep=""))

}

args <- commandArgs(TRUE)
print(args)
library('foreign')

# data source
fileimp <- args[1] # R indexes from 1...n
inputfile <- args[2] 
selectionvar <- scan(inputfile, what = "", nlines=1) # selection variable index
selrange <- scan(inputfile, nlines=1, what = "", skip= 1,sep=" ") # selection variable classes  
genevector <- scan(inputfile, what = "", nlines=1, skip=2, sep=" ") # gene column names
traitvector <- scan(inputfile, what = "", nlines=1, skip=3, sep=" ") # trait column names

#genes <- input[2]
#traits <-  input[3]


#print(paste(selrange,genes,traits))
print(selrange)
print(genevector)
print(traitvector)

print(genevector[length(genevector):0])

if(is.integer(as.integer(selectionvar))){
  selectionvar = as.integer(selectionvar)
}

genevector = convertToInt(genevector)
traitvector  = convertToInt(traitvector)
#stop("test")
print(genevector)
print(traitvector)
#stop("")                                        # genes
#gIndex1 <- as.numeric(args[2]) 
#gIndex2 <- as.numeric(args[3])
# traits
#tIndex1 <- as.numeric(args[4])
#tIndex2 <- as.numeric(args[5])
# selection variable  
#selVar <- as.numeric(args[6])
# selection variable name 
#selVarName <- args[7]
# range
#range <- as.numeric(args[7: length(args)])
#print(paste("range", range))
#print(paste(fileimp, " ",gIndex1," ",gIndex2,  " ", selVar, " ", args))
print(selectionvar)
#fileimp<-"../Inter99All290606.sav"
#Redit: smplt<-importData(file=fileimp)
smplt<-read.spss(file=fileimp, to.data.frame=TRUE)
#, max.value.labels=10)
                                        #, ), use.value.labels = FALSE
#, trim_values = FALSE
#file.realpath(names(smplt))
#print(smplt)

#print(smplt[,"LDL"])
#print(smplt[,c(2)])
#write.table(smplt,"datafile.txt",sep=";",append=F,quote=F, col.names=T,row.names=F)
#stop("stop")

#RunEpistasisForClass(valueRange=range, smplt=smplt, selVar=selVar, geneIndex1=gIndex1, geneIndex2=gIndex2, traitIndex1=tIndex1,traitIndex2=tIndex2)

RunEpistasisForClass(valueRange=selrange, smplt=smplt, selVar=selectionvar, genelist=genevector, traitnamelist=traitvector)

warnings()
