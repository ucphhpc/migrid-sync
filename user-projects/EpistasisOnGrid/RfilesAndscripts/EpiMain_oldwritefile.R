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


#"convertToMatrix"<-function(arg)
#{
#  mat <- matrix(0,length(arg[[1]]), length(arg))
#  for(i in 1:length(arg)){
#    mat[,i]<-smplt[[i]]
#  }
#  mat
#}

"writeToFile"<-function(data,filename)
{
write.table(data,filename,sep="\t",append=T,quote=F, col.names=F,row.names=F)
}



"RunEpistasisForClass" <- function(valuerange, smplt, selVar, selName, geneIndex1, geneIndex2, traitIndex1, traitIndex2)
{
hnames<-names(smplt)

#Choose selection variable
selectvar<<-selVar #2
#Name selectionvariabel
nselvar<<-selName#"Gender"
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
#smplt
#levmax<-max(smplt[[c(var)]],na.rm=TRUE)
#levmax
#convertToMatrix(smplt)

#matnames<- names(smplt)
#smmat<-table(matnames, )#c("hej","med", "dig"))#, c(1,2,3))#length(smplt[[1]]), length(smplt))
#smmat<-table(smplt)

#smmat <- cbind(matnames)
#smmat <- cbind(smplt[[1]])

#names(smmat)
#for(i in matnames){
#  smmat[,i]<-smplt[[i]]
#}

#smmat

#length(smmat)
#names(smmat)
#names(smmat) <- matnames
#names(smmat)
#smmat
#stop("test")
#smpltmat <- matrix(0,length(smplt[[1]]), length(smplt))
#matnames<- names(smplt)
#length(smpltmat[,1])
#length(smplt)
#length(matnames)
#length(smpltmat[[1]])
#smpltmat
#for(i in 1:length(matnames)){
#  smpltmat[, i]<-smplt[[i]]
#}
#length(smpltmat)
#length(smpltmat[[1]])
#smpltmat


#smplt<-smplt[]
#class(smplt)
#length(smplt)
#length(smplt[[2]])
#smplt[[1]][[3]]
#genderlist<-smplt[[2]]
#genderlist<-smplt[, c(2)]
#genderlist<-smplt$GENDER

#genderlist


#levmax<-2
#levmax
#class(smplt)

#class(smplt[c(var)])

#testlist = list(1,2,3,4,2,5,2,6,7,NA)

#testmat<-matrix(1:42,6,7)




#testlist[testlist==2]

#testlist[c(FALSE, TRUE, FALSE, FALSE, TRUE, FALSE, TRUE, FALSE, FALSE, NA)]

#testlist ==2 

#testmat

#testmat[4]
#testmat[,4]
#testmat[4,]
#testmat[testmat[,2]==10]



#length(testmat[, c(4)])

#hej<-2
#hej
#hej2<-c(2)
#hej2

#smplt["GENDER"]

#names(smplt[c(var)])
#names(smplt[c(var)])


#str(smplt)
#smplt$GENDER

#smplt[, c("GENDER")]
#boolist <- smplt[,"GENDER"]==1
#class(boolist)
#length(boolist)
#genderframe<-smplt[smplt["GENDER"]==1]

#newframe<-data.frame(smplt[,boolist],length(boolist),length(smplt))

#testvec <-  c(1,2,5,6,7,9)
#testvec2 <-  c(T,F,T,F,T)
#class(testvec2)
#smplt[testvec2,]



#newframe<-smplt[boolist,]

#class(newframe)
#newframe

#genderlist2<-list()
#genderlist2 <- genderlist[!(genderlist == NA)]

#print(length(genderlist))

#class(genderlist[[1]])


#stop("Whatever")
#genderlist
#genderlist2
#class(genderlist)
#genderlist[genderlist > 1]
#genderlist

#pmax(genderlist, na.rm=TRUE)
#max(as.character(list(1,2,3,4, NA)), na.rm = TRUE)

#smplt$GENDER

#testlist
#max(as.double(as.character(list(1,2,3,4,NA))), na.rm = TRUE)

#help(max)

#smplt

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


write.table(logtitel,paste(logsave,logext,sep=""),sep="\t",append=T, quote=F,row.names=F, col.names=F)
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T, quote=F, row.names=F, col.names=F)
write.table(date(),paste(logsave,logext,sep=""),sep="\t",append=T, quote=F, row.names=F, col.names=F)
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(studyfile,paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(studyvar,paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(tablehead,paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T, quote=F, col.names=F,row.names=F)



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
  write.table(matrix(updatescreen,nrow=1),paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
  
  testno<-testno+1
  
  gene2r <- gene2r - 1	

  print("new gene2: "+gene2r)
  
  if(gene2r==gene1r) 
    break

  
}# end repeat statement
gene2r<-geneend
gene1r<-gene1r+1
print("new gene1: "+gene1r)
}# end calculations for all gene combinations in one class.
 #while statement:

	tblnum<-tblnum+1
	#used to avoid printing of headings all the time. Does not work properly after remodelling.

 }#end calculations for all classes...

numcalc<-matrix(c("Number of test actually calculated:",calcno,"ofnumber of tests:",totaltest),nrow=1)
endcalc<-matrix(c("End of calculations:",date()),nrow=1)

# Redit : added flags for printing format
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(numcalc,paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(" ",paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)
write.table(endcalc,paste(logsave,logext,sep=""),sep="\t",append=T,quote=F, col.names=F,row.names=F)



}


args <- commandArgs(TRUE)

library('foreign')
fileimp<-"../Inter99All290606.sav"
#Redit: smplt<-importData(file=fileimp)
smplt<-read.spss(file=fileimp, to.data.frame=TRUE)
#, max.value.labels=10)
                                        #, ), use.value.labels = FALSE
#, trim_values = FALSE
#file.realpath(names(smplt))
#print(smplt)

#write.table(smplt,"datafile.txt",sep="\t",append=F,quote=F, col.names=T,row.names=T)

#stop("stop")
#RunEpistasisForClass(class=2, smplt=smplt, selVar=2,
#selName="Gender", geneIndex1=74, geneIndex2=103, traitIndex1=7,
#traitIndex2=37)

RunEpistasisForClass(range=c(1,2), smplt=smplt, selVar=2,
selName="Gender", geneIndex1=74, geneIndex2=103, traitIndex1=7,
traitIndex2=37)

#RunEpistasisForClass(class=2, smplt=smplt, selVar=2, selName="Gender", geneIndex1=74, geneIndex2=75, traitIndex1=7, traitIndex2=7)

#warnings()
