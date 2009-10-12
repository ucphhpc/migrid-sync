#Epistatis: this is the parent script!!!

#Modifyed 1.7.09 by MF

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
#hnames<-names(smplt)
#valueRange is the partition variable
#Choose selection variable
selectvar<<-selVar #2
#Name selectionvariabel
#nselvar<<-hnames[selVar]#selName#"Gender"
#ovenstående bruges ikke!!!!?????

traits <<- traitnamelist
genes <- genelist

#SIGNIFICANCE LEVELS
#Signifcans level for epistasis
epistsign<<-0.05#SKAL DENNE VÆRE GLOBAL???????BRUGES JO KUN I STARTEN NEDENFOR, Jo hvis HWE genindføres
SignMainExp<<-0.05
#CORRECTION FOR MULITPLE TESTING
#Shall Bonferoni correction be used in selection of trait-summary?: ("T" = yes, everything else is no)
boncorT<-"T"

#Missing values to be excluded for genes
misv<<- -99
#Missing values to be excluded for traits
misvt<<- -99

#File extensions
hepiexts<<-".txt"
#Logile
logext<<-".txt"
################DONT WRITE ANYTHING BELOW THIS LINE#############################

#Number of classes
levmax<<-max(smplt[c(selectvar)],na.rm=T)

#Bonferoni corrections for genes 
#NBNBNB This should only be used if the gene-base have been stripped for monomorphic genes
numgene <<-length(genes)#this is total number of genes, not the same as number of genes tested
numtr<-length(traits)

#Logfile for progression of calcluations
logsave<-paste("Log progress of Epistasis") 

logtitel<-matrix(c("EPISTASIS LOGFILE"),nrow=1)
studyfile<-matrix(c("File:","","",fileimp),nrow=1)
studyvar<-matrix(c("Classification variable:",names(smplt[c(selectvar)])),nrow=1)
studyclass<-matrix(c("Nymber of clases:","",levmax),nrow=1)
studygenes<-matrix(c("Number of genes:","",numgene),nrow=1)
studytraits<-matrix(c("Number of traits:","",numtr),nrow=1)
#tablehead<-matrix(c("Test number","","Class","Time"),nrow=1)

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
#writeToFile(" ",paste(logsave,logext,sep=""))
#writeToFile(logana1,paste(logsave,logext,sep=""))


#Monomorphic gene file
Monosave<<-paste("Monomorphic genes")
MonoMorphTitle<-matrix(c("MONOMORPHIC GENES"),nrow=1)
studyfile<-matrix(c("File:","","",fileimp),nrow=1)
studyvar<-matrix(c("Classification variable:",names(smplt[c(selectvar)])),nrow=1)
studyclass<-matrix(c("Nymber of clases:","",levmax),nrow=1)
studygenes<-matrix(c("Number of genes:","",numgene),nrow=1)
studytraits<-matrix(c("Number of traits:","",numtr),nrow=1)
Monotablehead<-matrix(c("Genes","Class","Level"),nrow=1)

writeToFile(MonoMorphTitle,paste(Monosave,logext,sep=""))
writeToFile(" ",paste(Monosave,logext,sep=""))
writeToFile(date(),paste(Monosave,logext,sep=""))
writeToFile(" ",paste(Monosave,logext,sep=""))
writeToFile(studyfile,paste(Monosave,logext,sep=""))
writeToFile(" ",paste(Monosave,logext,sep=""))
writeToFile(studyvar,paste(Monosave,logext,sep=""))
writeToFile(" ",paste(Monosave,logext,sep=""))
writeToFile(studyclass,paste(Monosave,logext,sep=""))
writeToFile(studygenes,paste(Monosave,logext,sep=""))
writeToFile(studytraits,paste(Monosave,logext,sep=""))
#writeToFile(" ",paste(Monosave,logext,sep=""))

#Polymorphic gene file
Polysave<<-paste("Polymorphic genes")
MonoMorphTitle<-matrix(c("POLYMORPHIC GENES"),nrow=1)
#studyfile<-matrix(c("File:","","",fileimp),nrow=1)
#studyvar<-matrix(c("Classification variable:",names(smplt[c(selectvar)])),nrow=1)
#studyclass<-matrix(c("Nymber of clases:","",levmax),nrow=1)
#studygenes<-matrix(c("Number of genes:","",numgene),nrow=1)
#studytraits<-matrix(c("Number of traits:","",numtr),nrow=1)


writeToFile(MonoMorphTitle,paste(Polysave,logext,sep=""))
writeToFile(" ",paste(Monosave,logext,sep=""))
writeToFile(date(),paste(Polysave,logext,sep=""))
writeToFile(" ",paste(Polysave,logext,sep=""))
writeToFile(studyfile,paste(Polysave,logext,sep=""))
writeToFile(" ",paste(Polysave,logext,sep=""))
writeToFile(studyvar,paste(Polysave,logext,sep=""))
writeToFile(" ",paste(Monosave,logext,sep=""))
writeToFile(studyclass,paste(Polysave,logext,sep=""))
writeToFile(studygenes,paste(Polysave,logext,sep=""))
writeToFile(studytraits,paste(Polysave,logext,sep=""))
writeToFile(" ",paste(Polysave,logext,sep=""))

#Main effect gene file
Mainsave<<-paste("Main effects")
MonoMorphTitle<-matrix(c("GENES WITH MAIN EFFECT"),nrow=1)
studyfile<-matrix(c("File:","","",fileimp),nrow=1)
studyvar<-matrix(c("Classification variable:",names(smplt[c(selectvar)])),nrow=1)
studyclass<-matrix(c("Nymber of clases:","",levmax),nrow=1)
studygenes<-matrix(c("Number of genes:","",numgene),nrow=1)
studytraits<-matrix(c("Number of traits:","",numtr),nrow=1)
Monotablehead<-matrix(c("Genes","Class","Level"),nrow=1)

writeToFile(MonoMorphTitle,paste(Mainsave,logext,sep=""))
writeToFile(" ",paste(Mainsave,logext,sep=""))
writeToFile(date(),paste(Mainsave,logext,sep=""))
writeToFile(" ",paste(Mainsave,logext,sep=""))
writeToFile(studyfile,paste(Mainsave,logext,sep=""))
writeToFile(" ",paste(Mainsave,logext,sep=""))
writeToFile(studyvar,paste(Mainsave,logext,sep=""))
writeToFile(" ",paste(Mainsave,logext,sep=""))
writeToFile(studyclass,paste(Mainsave,logext,sep=""))
writeToFile(studygenes,paste(Mainsave,logext,sep=""))
writeToFile(studytraits,paste(Mainsave,logext,sep=""))
writeToFile(" ",paste(Mainsave,logext,sep=""))



#Run calculations for all classes...
tblnum<<-0#to avoid headings for every class
calcno<<-0#counts number of actual calculated tests

#Counters
testno<-0
teststart<-1
calcsign<-0

# edit : Only execute a selected range i.e. number of partitions 
for(lev in valueRange) {
	sval<<-lev
	#selectvec <- smplt[,c(selectvar)]==sval # lav en logical vector over filtret
           selectvec <- smplt[,selectvar]==sval #class number
           smpl<<-smplt[selectvec,] # new dataframe with selected cases (note: efterfølgende ',' )
           svarn <- names(smpl[selectvar])
	if (length(genes)<2){
	stop ("No range of genes has been selected")}

##Start test of all gene-combinations in the selected class.
#Filter out the overall monomorphic genes IN THE CLASS
#genes to be deleted
geneDel<-NULL
#genes to be used
geneL<-NULL

for(genF in genes){#filter out monmorphic genes
  	geneVectorA <<- factor(gsub(" ", "",as.character(smpl[, c(genF)])), exclude= c(NA,misv,misvt))
	if(length(levels(geneVectorA))<2){#print to monogenes
	gname<- names(smpl[c(genF)])
   	monoGen<-matrix(c(gname,sval,"General"),nrow=1)
	geneDel<-rbind(geneDel,monoGen)	
	}
	else{
	#Genes to used in epistasis
	geneL<-cbind(geneL,genF)}#to be printed?
}#End filtering monomorphic genes
geneL<<-geneL#to make it global
print("genes used")
print(geneL)
aaa<-names(smpl[c(geneL)])
print(aaa)
numGenes<<-length(geneL)





writeToFile(names(smpl[c(geneL)]),paste(Polysave,logext,sep=""))
matrixHead<-matrix(names(smpl[c(geneL)]),nrow=1)
#Set signifcance level (Bonferoni)

numgene <<-length(geneL)
numtest<<-numgene*(numgene-1)/2
if(boncorT=="T")
	{epistsign<<-epistsign/(numtest*levmax*numtr)} else{epistsign==epistsign}

#Significance level for main effects #ponder and ask stat-people
	SignMain<<-SignMainExp/numtest

#Write to logfile
logana1<-matrix(c("Significance level:","","",format(epistsign,digits=4,scientific = TRUE)),nrow=1)
logana2<-matrix(c("Significance level main effects:","",format(SignMain,digits=4,scientific = TRUE)),nrow=1)
writeToFile(logana1,paste(logsave,logext,sep=""))
writeToFile(logana2,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
#



#Summary of monomorphic genes
genesOut<-unique(geneDel)
  monoGeneS<-matrix(c(paste("Number of monomorphic genes in class",sval,":"),numgene-length(geneL)),nrow=1)
  epiGene<-matrix(c(paste("Number of non-monomorphic genes in class",sval,":"),length(geneL)),nrow=1)
  writeToFile("",paste(Monosave,logext,sep=""))
  writeToFile(monoGeneS,paste(Monosave,logext,sep=""))
  writeToFile(epiGene,paste(Monosave,logext,sep=""))
  writeToFile("",paste(Monosave,logext,sep=""))
  writeToFile(Monotablehead,paste(Monosave,logext,sep=""))
  writeToFile("",paste(Monosave,logext,sep=""))
  writeToFile(genesOut,paste(Monosave,logext,sep=""))
  writeToFile("",paste(Monosave,logext,sep=""))

#Write to logfile
  writeToFile(epiGene,paste(logsave,logext,sep=""))
  writeToFile("",paste(logsave,logext,sep=""))
  traitsum1<-matrix(c("Summary of traits:"),nrow=1)
  traitsum2<-matrix(c("Trait","Mean","Variance","Possible epistasis","Signifcant epistasis"),nrow=1)
  writeToFile(traitsum1,paste(logsave,logext,sep=""))
  writeToFile("",paste(logsave,logext,sep=""))
  writeToFile(traitsum2,paste(logsave,logext,sep=""))
  writeToFile("",paste(logsave,logext,sep=""))

#
#print(paste("Partition","Class","Trait","Gene1","Gene2"))#to many outputs; for test purposes only

print(paste("TestNo","Partition","Class","Trait","Gene","Time"))


#Generate general matrix with all genes except the excluded above

generalMatr<<-matrix(data=0,nrow=numGenes,ncol=numGenes,dimnames = list(names(smpl[c(geneL)]),names(smpl[c(geneL)])))#maybe not global


#Main effect genes file
MainEffect<<-NULL
#Monomorph genes file
monoG<<-NULL

#Select TRAIT
for(traitn in traits){
  trait<<-names(smpl[c(traitn)])
  traitVector <<- as.numeric(smpl[, c(trait)]) # we need to make traitVector global ("<<-" instead of "<-")
  traitmean<<-mean(na.omit(traitVector))
  traitvar <<-var(na.omit(traitVector))
  lognum<<-0#to avoid headings in log-files. NB different loop than tblnum

#Matrices for betavalues of main and epi effects in anova
mainBetaMatr<<-generalMatr
EpiBetaVarMatr<<-generalMatr
MainVarMatr<<-generalMatr

#Initiate summaries of variances, betavalues etc
#trlogsum contains sign-levels, relative amount of genetic varaince, and comments
trlBind<<-NULL
#blogsum contains actual variances and betabalues
blogBind<<-NULL


#Now select GENES
#Select first gene
#print("before gene1 select")
for(gene1 in geneL){
#for(gene1 in 1:length(geneL)){
 
#print("i first gene selct")
          gene1<<-gene1
          gname1<<- names(smpl[c(gene1)])
          geneVectorA <<- factor(gsub(" ", "",as.character(smpl[, c(gname1)])), exclude= c(NA,misv,misvt))
          geneVector1<<-as.numeric(geneVectorA)#MERGE med do eller få omskrevet til original senere


#bbb<-names(smpl[gene1]) #exactly the same as gname1 above

#print("genvector1")
#print(geneVector1)
#print(nlevels(as.factor(geneVector1)))
#print(levels(as.factor(geneVector1)))
#print(length(as.factor(geneVector1)))
#print(length(geneVector1))#same as above with as.factor

#Exclude gene if monomorphic for the trait and continue with the next gene
	if(nlevels(as.factor(geneVector1))<2){#print to monogenes
   	   monoGene<-matrix(c(gname1,sval,trait),nrow=1)
	   monoG<<-rbind(monoG,monoGene)
	   next}#end printing of monomorphic gene1

#Still inside for(gene1 in geneL
#Select second gene

#Includes genes filtered out; waist of time
#print(geneL[74])
#lll<-levels(as.factor(geneL))
#print(lll)
#print(length(lll))
#print(lll[74])
#mmm<-as.numeric(lll)
#print(c(lll))
#print(mmm)
#print(mmm[74])

#print("bb")
#bb<-length(geneL)
#print(bb)
#dd<-levels(as.factor(geneL))
#print(dd)
#ee<-as.numeric(dd)
#print(ee)

#print("gene1")
#print(gene1)

#ff<-c(ee)
#print(ff)

#for(xx in 1:length(geneL)){print(xx)
#print(dd[xx])
#}


#for(gene2 in geneL){

#if(gene1==gene2){next}
#print(gene2)}

#bla

##NBNBNB som det står i for-statementet spildes der tid på at test tidligere kaserede monomorphe gener
#	for(gene2 in gene1:geneL){
#	for(gene2 in gene1:geneL){
	for(gene2 in geneL[length(geneL)]:gene1){
          	    if(gene1 == gene2){break}#ændres til next??
#if(gene1==gene2){next}
#                  gname2<<- names(smpl[c(gene2)])
#gene2<<-yy
                  gname2<<- names(smpl[c(gene2)])
#gname2<-names(smpl[c(geneL)][gene2])
# print(gname2)
                 geneVectorB <<- factor(gsub(" ", "",as.character(smpl[, c(gname2)])), exclude=c(NA,misv,misvt))
                 geneVector2<<-as.numeric(geneVectorB)#MERGE med do eller få omskrevet til original senere
                 gene2<<-gene2

#Test monitoring; disable later
print(paste(svarn,sval,trait,gene1,gname1,gene2,gname2))#Drop later as to many and quick prints are produced

#ID for subjects
	SubjID<-c(as.character(smpl[,1]))
##Construct operating data frame
	qtrait<-data.frame(SubjID,geneVector1,geneVector2,traitVector)
	traittrimX<<-as.data.frame(qtrait[(!is.na(qtrait[1]) & !is.na(qtrait[2]) & !is.na(qtrait[3])& !is.na(qtrait[4])),(1:4)])
	traittrim<<-data.frame(traittrimX[2:4],row.names=traittrimX[,1])

#	traittrim<<-as.data.frame(qtrait[(!is.na(qtrait[1]) & !is.na(qtrait[2]) & !is.na(qtrait[3])),(1:3)])
#If one of the genes become monomorph, then drop and continue to the next second gene.

#Outputs for minitoring and debugging
#print(paste("Dimension","Levels","G1","G2","Trait"))
#tr1<-dim(traittrim)[1]
#tr2<-nlevels(as.factor(traittrim[,1]))
#tr3<-nlevels(as.factor(traittrim[,2]))
#tr4<-nlevels(as.factor(traittrim[,3]))
#print(paste(tr1,"            ",tr2,"",tr3,"",tr4))

#The combined file is evaluated here for monomorphs

	if(nlevels(as.factor(traittrim[,1]))<2){next}
	if(nlevels(as.factor(traittrim[,2]))<2){next} 

#FORMER END	}#end selection of gene 2, and none of the genes should be monomorphic or empty

#Still inside in gene 2 select

	if(is.null(traittrim)){
	print("no trait")
	print(trait)
	next}

#If more than 3 levels are present for gene 1 and 2 skip
#This is only a database control and should not be possible
	if(nlevels(as.factor(traittrim[,1]))>3){
print("more than three levels")
print(gname1)
	next}#end 4-level test for gene1
#and gene2...
	if(nlevels(as.factor(traittrim[,2]))>3){
print("more than three levels")
print(gname2)
	next}#end 4-level test for gene2


#This is a simple test for unbalanced data    MOVE DOWN after test for monomorphism 
           crosst<-table(as.factor(traittrim[,1]),as.factor(traittrim[,2]),dnn = c(gname1,gname2))
	ChiPvalue<-summary(crosst)$p.value
	#It is a test of unbalanced snps, which could be caused by epistasis or HWD. For the moment, just print a message
	if(ChiPvalue=="NaN"){SnpMessage<<-""}
	   else{if(ChiPvalue<epistsign){SnpMessage<<-"Unblanced SNPs"}
	          else{SnpMessage<<-""}

 #AND NOW CALCULATIONS!

  calcnum<-DistrPost()

  lognum<<-lognum+1

  calcsign<-calcsign + calcnum}

  testno<-testno+1#???????????

#   updatescreen<-c(testno,"of",numtest,sval,date(),sep="")
	}#end selection of gene 2, and none of the genes should be monomorphic or empty MOVE???
#print(paste(testno,svarn,sval,trait,gname1,date()))  
}# end gene repeat statement



#Variance and beta outputs
endcalc<-matrix(c("End of calculations:",date()),nrow=1)
##Relative genetic value aoutputs output

numEpistTrait<-length(geneL)*(length(geneL)-1)/2
nomEpiPoss<-matrix(c("Number of possible epistatic values:",numEpistTrait),nrow=1)

#numcalc<-matrix(c("Number of significant epistasis:",calcsign,"of possible number in the class",":",relNumEpi,"%"),nrow=1)
#relNumEpiTrait<-format(trldim*100/numEpistTrait,digits = 3,nsmall=2)

trldim<-dim(trlBind)[1]
relNumEpiTrait1<-format(trldim*100/numEpistTrait,digits = 3,nsmall=2)

if(is.null(trldim)){trldim<-0}
trvardim<-matrix(c("Number of epistatic interactions:",paste(trldim,"(",relNumEpiTrait1,"%)")),nrow=1)
tupdates1<-matrix(c("","","","","","Significant epistasis","Genetic variance (fractions)"),nrow=1)
tupdates2<-matrix(c("Number","Mean","Variance","Gene 1","Gene 2", "pCR", "pAnova","GenV/TotV","AddV/GenV","DomV/GenV","EpiV/GenV","Notes"),nrow=1)

writeToFile(nomEpiPoss,paste(traitsavelogSig,hepiexts))
writeToFile(trvardim,paste(traitsavelogSig,hepiexts))
writeToFile("",paste(traitsavelogSig,hepiexts))
writeToFile(tupdates1,paste(traitsavelogSig,hepiexts))
writeToFile(tupdates2,paste(traitsavelogSig,hepiexts))
writeToFile(trlBind,paste(traitsavelogSig,hepiexts))
writeToFile("",paste(traitsavelogSig,hepiexts))
writeToFile(endcalc,paste(traitsavelogSig,hepiexts))

#Varaince and beta values
bvdim<-dim(blogBind)[1]
relNumEpiTrait2<-format(bvdim*100/numEpistTrait,digits = 3,nsmall=2)
bevadim<-matrix(c("Number of epistatic interactions:",paste(bvdim,"(",relNumEpiTrait2,"%)")),nrow=1)
bupdates1<-matrix(c("","","","Variances","","","","","Beta-values"),nrow=1)
bupdates2<-matrix(c("Number","Gene 1","Gene 2","PhenoV","GenV","AddV","DomV","EpiV","BAGene1","BAGene2","BEpi"),nrow=1)

writeToFile(nomEpiPoss,paste(BetasavelogSig,hepiexts))
writeToFile(bevadim,paste(BetasavelogSig,hepiexts))
writeToFile("",paste(BetasavelogSig,hepiexts))
writeToFile(bupdates1,paste(BetasavelogSig,hepiexts))
writeToFile(bupdates2,paste(BetasavelogSig,hepiexts))
writeToFile(blogBind,paste(BetasavelogSig,hepiexts))
writeToFile("",paste(BetasavelogSig,hepiexts))
writeToFile(endcalc,paste(BetasavelogSig,hepiexts))

#Summary output to logfile
logana3<-matrix(c(trait,format(traitmean,digits = 3,nsmall=2),format(traitvar,digits = 3,nsmall=2),numEpistTrait,"",paste(trldim,"(",relNumEpiTrait1,"%)")),nrow=1)
writeToFile(logana3,paste(logsave,logext,sep=""))

#format(traitvar,digits = 3,nsmall=2))
#

#MATRIX OUTPUTS
#Write main-betas to file. Gene1 upper rigth triangle, gene2 lower left triangle

MainBetaSaveR<-paste("Main beta values raw",names(smpl[c(selectvar)]),trait) 
MainBetaSaveH<-paste("Main beta values headings",names(smpl[c(selectvar)]),trait) 
writeToFile(matrixHead,paste(MainBetaSaveH,logext,sep=""))
writeToFile(mainBetaMatr,paste(MainBetaSaveH,logext,sep=""))
writeToFile(mainBetaMatr,paste(MainBetaSaveR,logext,sep=""))
#Write add-dom variance to file
MainVarSaveR<-paste("Add and dom variances raw",names(smpl[c(selectvar)]),trait) 
MainVarSaveH<-paste("Add and dom variances headings",names(smpl[c(selectvar)]),trait) 
writeToFile(matrixHead,paste(MainVarSaveH,logext,sep=""))
writeToFile(MainVarMatr,paste(MainVarSaveH,logext,sep=""))
writeToFile(MainVarMatr,paste(MainVarSaveR,logext,sep=""))

#Write epistasis variance and betas to file. Variance upper rigth triangle, betas lower left triangle

EpiBetaSaveR<-paste("Epistasis var and beta values raw",names(smpl[c(selectvar)]),trait) 
EpiBetaSaveH<-paste("Epistasis var and beta values headings",names(smpl[c(selectvar)]),trait) 
writeToFile(matrixHead,paste(EpiBetaSaveH,logext,sep=""))
writeToFile(EpiBetaVarMatr,paste(EpiBetaSaveH,logext,sep=""))
writeToFile(EpiBetaVarMatr,paste(EpiBetaSaveR,logext,sep=""))

}# end calculations for all gene combinations in one class.
#Write main effects to file

  MainU<-unique(MainEffect)
  NumbMain<-dim(MainU)[1]
  nomMain<-matrix(c(paste("Number of genes with main effect in class",sval,":"), NumbMain),nrow=1)
  writeToFile(monoGeneS,paste(Mainsave,logext,sep=""))
  writeToFile(epiGene,paste(Mainsave,logext,sep=""))
  writeToFile(" ",paste(Mainsave,logext,sep="")) 

  writeToFile(nomMain,paste(Mainsave,logext,sep=""))
  writeToFile(" ",paste(Mainsave,logext,sep="")) 
  writeToFile(MainU,paste(Mainsave,logext,sep=""))

#Save monomorphic genes in the class for all traits
#If we want the actual number of epistais calsulated 
	monoM<-unique(monoG)
	numEpist<-(length(geneL)*(length(geneL)-1)/2)*numtr
	dmonoG<-dim(monoM)[1]
           nomEpiPossible<-matrix(c(paste("Number of possible epistatic values in class",sval,":"),numEpist),nrow=1)
           writeToFile(nomEpiPossible,paste(Monosave,logext,sep=""))

     if(is.null(dmonoG)){
           nomgene<-matrix(c(paste("No monomorphic genes (all traits) in class",sval,":",0)),nrow=1)
           writeToFile(nomgene,paste(Monosave,logext,sep=""))
           writeToFile("",paste(Monosave,logext,sep=""))
           writeToFile(monoM,paste(Monosave,logext,sep=""))
           }
	else{
	mGene<-matrix(c(paste("Number of monomorphic genes (all traits) in class",sval,":"),dmonoG),nrow=1)
           writeToFile(mGene,paste(Monosave,logext,sep=""))
           writeToFile("",paste(Monosave,logext,sep=""))
	MonotableTrait<-matrix(c("Genes","Class","Trait"),nrow=1)
           writeToFile(MonotableTrait,paste(Monosave,logext,sep=""))
	writeToFile("",paste(Monosave,logext,sep=""))
           writeToFile(monoM,paste(Monosave,logext,sep=""))
	}


   tblnum<-tblnum+1
   #used to avoid printing of headings all the time. Does not work properly after remodelling.

 }#end calculations for all genes and traits in the class...
#format(vartrait, digits = 3,nsmall=2))
relNumEpi<-format(calcsign*100/numEpist,digits = 3,nsmall=2)
numcalc<-matrix(c("Number of significant epistasis:",calcsign,"of possible number in the class",":",relNumEpi,"%"),nrow=1)
endcalc<-matrix(c("End of calculations:",date()),nrow=1)

# Redit : added flags for printing format

#  writeToFile(epiGene,paste(logsave,logext,sep=""))
           writeToFile("",paste(logsave,logext,sep=""))
           writeToFile(nomEpiPossible,paste(logsave,logext,sep=""))

	mGene<-matrix(c(paste("Number of monomorphic genes (all traits) in class",sval,":"),dmonoG),nrow=1)
           writeToFile(mGene,paste(logsave,logext,sep=""))
           writeToFile("",paste(logsave,logext,sep=""))
	MonotableTrait<-matrix(c("Genes","Class","Trait"),nrow=1)

writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(numcalc,paste(logsave,logext,sep=""))
writeToFile(" ",paste(logsave,logext,sep=""))
writeToFile(endcalc,paste(logsave,logext,sep=""))

}

#####
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
#print(selrange)
#print(genevector)
#print(traitvector)

#print("selectionvar")
#print(selectionvar)

#print(genevector[length(genevector):0])

if(is.integer(as.integer(selectionvar))){
  selectionvar = as.integer(selectionvar)
}

genevector = convertToInt(genevector)
traitvector  = convertToInt(traitvector)
#stop("test")
#print(genevector)
#print(traitvector)
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
#print(selectionvar)
#fileimp<-"../Inter99All290606.sav"

#smplt<-scan(file=fileimp,what="numeric")

#smplt<-as.data.frame(fileimp)
#print(smplt)
#bla
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
