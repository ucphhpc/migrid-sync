#Epistatis: this is the working script!!!

#UDVIKLING I den menustyrede version bør genotyperne klassificeres som AA, Aa og aa, således at programmet kan identificere homozygote
#og heterozygote. Kun re-klassificerede gener kan testes, og i øvrigt skal det være muligt at vælge hvilke gener der skal indgå i
#undersøgelserne. Ligeledes skal traits også kunne vælges frit, og ikke som nu være afhængig af en samlet liste.
#De traits sm testes for significans anføres p-value.
#Er der stadig et problem med at monogene typer testes for diseq??
#VEd sammenligning af traits mellem haplotyper opstår en dobbelt-bestemmesle af to habplotyper
#men resultatet er forskelligt.
#Pgra. afbrydelser laves log-filer der kan bruges til genoptagelse.
#Logfiler i epistasis registrerer ikke sign. resultater. Men strukturen synes nogenlunde OK!
#I det hele taget er Epifilerne
#alt for mange. Helt klart df-fil med multiple spørgsmåls-scripter.
#HUSK at inkorporere alla former for ikke-svar dvs Na NaN og inf (mere?)
#Drop single-gene var her og brug Falconer fra Heritability
#Kan det være rigtigt at LD ikke kan beregnes hvis hvert gen kun har to genotyper?
#Udskriv en råfil som txt til EpiEval, haplo etc
#NBNBNB nogle gen var er over 1 efter deling med to var. Solve!
#NBNB F-test has min p-value of 1.1e-16. Upto e-14 it is heavely rounded. Thats in S6.2. what about S7.0 and byond??64BIT??
#OUTputtet til videre behandling (se working files) skal ændres til en blok hvor al tekst er på engelsk!!



"writeToFile"<-function(data,filename)
{
write.table(data, filename, sep="\t", append=T, quote=F, col.names=F, row.names=F)
}


"RunEpistasis" <- function(smplt, selVar, geneIndex1, geneIndex2, traitIndex1, traitIndex2)
{
hnames<-names(smplt)

#Choose selection variable
selectvar<<-selVar #2
#Name selectionvariabel
nselvar<<-hnames[selVar]#selName#"Gender"
#Select gene1
genenr1 = geneIndex1#74
#Select gene2
genenr2 = geneIndex2#103
#First trait
trait1<<-traitIndex1#7
#Last trait
trait2<<-traitIndex2#37

#SIGNIFICANCE LEVELS
#Signifcans level for epistasis
epistsign<<-0.05

#CORRECTION FOR MULITPLE TESTING
#Shall Bonferoni correction be used in selection of trait-summary?: ("T" = yes, everything else is no)
boncorT<-"T"

#Missing values to be excluded for genes
misv = "?"
#Missing values to be excluded for traits
misvt<<- -99

#Rounding results in tables#not in use pt
rdn<-20

#Epistasis
epiext<<-".qpw"
#Epistais summary
epiexts<<-".qpw"
#Epistasis and heritabilities summary
hepiexts<<-".qpw"
#Logile
logext<<-".txt"
#Eval-file
evalext<<-".txt"

################DONT WRITE ANYTHING BELOW THIS LINE#############################

#Number of classes
levmax<<-max(smplt[c(selectvar)],na.rm=T)

#Bonferoni corrections for genes
numgene<<-abs(genenr2-genenr1)+1
numtest<-numgene*(numgene-1)/2

#Bonferoni corrections for epistasis

numtr<-abs(as.numeric(trait2)-as.numeric(trait1)+1)
if(boncorT=="T")
	{epistsign<-epistsign/(numtest*levmax*numtr)} else{epistsign=epistsign}

totaltest<-numtest*levmax

#Logfile for progression of calcluations
logsave<-paste("Log progress of Epistasis") 

logtitel<-matrix(c("EPISTASIS"),nrow=1)
studyfile<-matrix(c("File:","",fileimp),nrow=1)
studyvar<-matrix(c("Classification variable:"," ",names(smplt[c(selectvar)])),nrow=1)
tablehead<-matrix(c("Test number","","Class","Gene1","Gene2","Action","Time"),nrow=1)

# Redit : Default write.table() writes to file differently than in S, so we need to add flags "quote=F, col.names=F,row.names=F"
#write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(logtitel,paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(date(),paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(studyfile,paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(studyvar,paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(tablehead,paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T)
#write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T, quote=F, col.names=F,row.names=F)

writeToFile(logtitel,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(date(),paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(studyfile,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(studyvar,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(tablehead,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))

#Run calculations for all classes...
tblnum<<-0#to avoid headings for every class
lognum<<-0#to avoid headings in log-files. NB different loop than tblnum
calcno<<-0#counts number of actual calculated tests

#Counter
testno<-1

#Start test of one class at a time
for(lev in 1:levmax) {
	sval<<-lev
            
if(sval>levmax || sval<1)stop("Levels out of bounce")
	tfilt <- paste(names(smplt[c(selectvar)]), "=", sval)
        
	# importer alle rækker med pågældende filter ("gender = 1")
	#Redit: smpl <- importData(file=fileimp, filter = tfilt)
	selectvec <- smplt[,c(selectvar)]==sval # lav en logical vector over filtret
        #boolist <- smplt[,"GENDER"]==1
	#smpl <- read.spss(file=fileimp)
        smpl<<-smplt[selectvec,] # lav ny dataframe med udvalgte rækker (note: efterfølgende ',' )
        svarn <- names(smpl[c(selectvar)])

        
if (genenr1==genenr2){
    stop ("No range of genes has been selected")}
	else {if (genenr1>genenr2)
		     {gene1r<-genenr2
 			  gene2r<-genenr1}
			  else
			 {gene1r<-genenr1
 			  gene2r<-genenr2}
 }#end if(sval>levmax ....

###

geneend<-	gene2r

#Start test of all gene-combinations in thje selected class.
while(gene1r <gene2r) {
repeat{	
  gname1<<-names(smplt[c(gene1r)])
  gname2<<-names(smplt[c(gene2r)])
  
  # alle gname1 og gname2 gener for en klasse(GENDER) 

  # Redit : geneVector1 <- factor(as.character(smpl[, c(gname1)]), exclude=misv)
  # alternate: geneVector1 <- factor(as.character(smpl[c(gname1)]), exclude=misv)
  # blank spaces must be removed (gsub) in order for "exclude" to match "?"
  # benja note: "factor" gør at geneVector1-2 kun indeholder 1 level for hver gen værdi
  geneVector1 <<- factor(gsub(" ", "",as.character(smpl[, c(gname1)])), exclude=misv)
  
  # Redit : geneVector2 <- factor(as.character(smpl[, c(gname2)]), exclude=misv)
  # alternate: geneVector2 <- factor(as.character(smpl[c(gname2)]), exclude=misv)
  # blank spaces must be removed (gsub) in order for "exclude" to match "?"
  geneVector2 <<- factor(gsub(" ", "",as.character(smpl[, c(gname2)])), exclude=misv)

  #vec <- as.character(strtrim(smpl[, c(gname2)], 2))
  #print(vec)
  #print(class(vec))
  #print(factor(as.character(smpl[, c(gname2)])))
  #print(factor(gsub(" ", "",as.character(smpl[, c(gname2)])), exclude=misv))
  
  crosst<-table(geneVector1,geneVector2)

#print(geneVector1)
#print(geneVector2)
#To avoid df=0 in aov, var.test and t.test
#This is not enough, as some genotypes may be deleted as the dependent variable may be deleted, deleting the genotype.
#By this a gene may end up as monogenic, and results in df=0
#Therefor this must be tested in EpCR-script (or in DistrPost)
if(dim(crosst)[1]<2){firstacc=0}
	else{firstacc=1}
if(dim(crosst)[2]<2){secondacc=0}
	else{secondacc=1}
	matacc<-firstacc+secondacc
			
if(matacc<2){
    action<-"Skip"
	}
else{
     #AND NOW CALCULATIONS!
  
  signtraits<-DistrPost()
  action<-"Calc"
  calcno<-calcno+1
  lognum<-lognum+1
}
#signtraits bruges ikke pt(DistrPost kaldes dog!!)

  updatescreen<-c(testno,"of",totaltest,sval,gname1,gname2,action,date(),sep="")
#Redit: print(c("Test No:",updatescreen)) # udskrifter
# Redit: added flags for printing format
  writeToFile(matrix(updatescreen,nrow=1),paste(logsave,logext,sep=""))
  print(updatescreen)
  testno<-testno+1
  
  gene2r <- gene2r - 1	

  print(paste("new gene2: ",gene2r))
  
  if(gene2r==gene1r) 
    break

  
}# end repeat statement
gene2r<-geneend
gene1r<-gene1r+1
print(paste("new gene1: ",gene1r))
}# end calculations for all gene combinations in one class.
 #while statement:

	tblnum<-tblnum+1
	#used to avoid printing of headings all the time. Does not work properly after remodelling.

 }#end calculations for all classes...

numcalc<-matrix(c("Number of test actually calculated:",calcno,"ofnumber of tests:",totaltest),nrow=1)
endcalc<-matrix(c("End of calculations:",date()),nrow=1)

# Redit : added flags for printing format
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(numcalc,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(endcalc,paste(logsave,logext,sep=""))

}

library('foreign')
# data source
fileimp <-  "Inter99All290606.sav"
# genes
gIndex1 <- 85 
gIndex2 <- 90 
# traits
tIndex1 <- 7
tIndex2 <- 37
# selection variable  
selVar <- 2

smplt<-read.spss(file=fileimp, to.data.frame=TRUE)

RunEpistasis(smplt=smplt, selVar=selVar, geneIndex1=gIndex1, geneIndex2=gIndex2, traitIndex1=tIndex1,traitIndex2=tIndex2)

