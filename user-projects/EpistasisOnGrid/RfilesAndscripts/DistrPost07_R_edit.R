#Revised by MF 21.may 2009 
#All traits are tested with the selected two genes in EpiMain

"DistrPost"<-function()
{
#print("In distr")
#NB HWE assumed (and can be tested) that is blanced data
#Priming list for significant traits

##stoppe her??
#Trait mean 
meantrait<-mean(traittrim[3])#NB This is grand mean for the trait

#Trait variance
   vartrait<-var(traittrim[3])[1] # "...unbiased arguement unused..."

##CHECK var komandoen i R: Unbiased at der divideres med N-1, dvs sample var, men division med N betyder populations var


##############

#Selection of cases according to haplotype. Non-valid traits excluded. 
#The actual traitvalues are included, not the mean-corrected.OK!!
#Can this be done by using the cross-tab above??I think however, that the cpu-time may not
#be reduced, but the benefit is that other types of gene-variations may be included, particular
#microsatelites witch may have 10 or more values. This is not an issue right now, the issue is to 
#reduce computing time

gdfAABB<-traittrim[(traittrim[1]=="1" & traittrim[2]=="1"),3]
gdfAABb<-traittrim[(traittrim[1]=="1" & traittrim[2]=="2"),3]
gdfAAbb<-traittrim[(traittrim[1]=="1" & traittrim[2]=="3"),3]
gdfAaBB<-traittrim[(traittrim[1]=="2" & traittrim[2]=="1"),3]
gdfAaBb<-traittrim[(traittrim[1]=="2" & traittrim[2]=="2"),3]
gdfAabb<-traittrim[(traittrim[1]=="2" & traittrim[2]=="3"),3]
gdfaaBB<-traittrim[(traittrim[1]=="3" & traittrim[2]=="1"),3]
gdfaaBb<-traittrim[(traittrim[1]=="3" & traittrim[2]=="2"),3]
gdfaabb<-traittrim[(traittrim[1]=="3" & traittrim[2]=="3"),3]

#number of haplotypes Obsolete??? Used for calculating size of sample
ltr1<-length(gdfAABB)
ltr2<-length(gdfAABb)
ltr3<-length(gdfAAbb)
ltr4<-length(gdfAaBB)
ltr5<-length(gdfAaBb)
ltr6<-length(gdfAabb)
ltr7<-length(gdfaaBB)
ltr8<-length(gdfaaBb)
ltr9<-length(gdfaabb)

#Usefull vectors and values
trlength<-c(ltr1,ltr2,ltr3,ltr4,ltr5,ltr6,ltr7,ltr8,ltr9)
trcontent<-list(gdfAABB,gdfAABb,gdfAAbb,gdfAaBB,gdfAaBb,gdfAabb,gdfaaBB,gdfaaBb,gdfaabb)
trmean<-c(mean(gdfAABB),mean(gdfAABb),mean(gdfAAbb),mean(gdfAaBB),mean(gdfAaBb),mean(gdfAabb),mean(gdfaaBB),mean(gdfaaBb),mean(gdfaabb))

#Number of cases
sumcases<-sum(trlength)#as casenumbe do
eheadtrait2<-matrix(c(sumcases,format(meantrait, digits = 3,nsmall=2),format(vartrait, digits = 3,nsmall=2)),nrow=1)

##Allele frequnces to calculate variance in EpiLW
#NB Try to calcluate variance from EpiCR, or calculate significance from EpiLW
AAgeno<-ltr1 + ltr2 + ltr3
Aageno<-ltr4 + ltr5 + ltr6
aageno<-ltr7 + ltr8 + ltr9
BBgeno<-ltr1 + ltr4 + ltr7
Bbgeno<-ltr2 + ltr5 + ltr8
bbgeno<-ltr3 + ltr6 + ltr9
allelA<-(2*sum(AAgeno) + sum(Aageno))/(2*sumcases)#Summary stat but not used otherwise
allela<-(2*sum(aageno) + sum(Aageno))/(2*sumcases)
allelB<-(2*sum(BBgeno) + sum(Bbgeno))/(2*sumcases)
allelb<-(2*sum(bbgeno) + sum(Bbgeno))/(2*sumcases)

allFreq<-c(allelA,allela,allelB,allelb)

################

#Headings for outputs
#Necesary to do here, as traits are accessed succesively in this script, not in main script
traitsavelogSig<<-paste("Epistasis ",names(smplt[c(selectvar)]),trait) 
tlogana1<-matrix(c("EPISTASIS calculations."),nrow=1)
tlogana2<-matrix(c("Only haplotypes with significant epistasis are printed."),nrow=1)
tlogana2a<-matrix(c("Additive and dominant effects are two-effects."),nrow=1)
tlogana3<-matrix(c("Significance level:","","",format(epistsign,digits=4,scientific = TRUE)),nrow=1)
tlogana4<-matrix(c("Significance level main effects:","",format(SignMain,digits=4,scientific = TRUE)),nrow=1)

tlogfile<-matrix(c("File:","","",fileimp),nrow=1)
tloghead1<-matrix(c("Classification variable:","",names(smplt[c(selectvar)])),nrow=1)
trheadtrait<-matrix(c("Trait:"," ","","",trait),nrow=1)
#tlogcasenumber<-matrix(c("Number of cases:","","",sumcases),nrow=1)
tlogcasemean<-matrix(c("Trait mean:","","",format(traitmean, digits = 2,nsmall=2)),nrow=1)
tlogcasevar<-matrix(c("Trait variance:","","",format(traitvar,digits = 2,nsmall=2)),nrow=1)
tloghead2<-matrix(c("Number of classes:","","",levmax),nrow=1)
tloghead3<-matrix(c("Number of genes:","","",numgene),nrow=1)
tloghead4<-matrix(c("This is class","","",sval),nrow=1)

#Var and beta headings special
BetasavelogSig<<-paste("Variance and beta-values",names(smplt[c(selectvar)]),trait) 
bheading<-matrix(c("VARIANCE and BETA-VLAUES"),nrow=1)

#MF comment eventually cut HWE and Haplotype stat if it consumes time!Interesting stuff but may be calculated separately for positiv epi-pairs

if(lognum==0){
#kun overskrifter een gang

#summary signifcant only
#This file only contains the bonferoni corrected significant epistasis.
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tlogana1,paste(traitsavelogSig,hepiexts))
writeToFile(tlogana2,paste(traitsavelogSig,hepiexts))
writeToFile(tlogana2a,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(date(),paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tlogfile,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tloghead1,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(trheadtrait,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tloghead2,paste(traitsavelogSig,hepiexts))
writeToFile(tloghead3,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tloghead4,paste(traitsavelogSig,hepiexts))
#writeToFile(tlogcasenumber,paste(traitsavelogSig,hepiexts))
writeToFile(tlogcasemean,paste(traitsavelogSig,hepiexts))
writeToFile(tlogcasevar,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tlogana3,paste(traitsavelogSig,hepiexts))
writeToFile(tlogana4,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))

#This file only contains the variances and beta-values
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(bheading,paste(BetasavelogSig,hepiexts))
writeToFile(tlogana2,paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(date(),paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(tlogfile,paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(tloghead1,paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(trheadtrait,paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(tloghead2,paste(BetasavelogSig,hepiexts))
writeToFile(tloghead3,paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(tloghead4,paste(BetasavelogSig,hepiexts))
#writeToFile(tlogcasenumber,paste(BetasavelogSig,hepiexts))
writeToFile(tlogcasemean,paste(BetasavelogSig,hepiexts))
writeToFile(tlogcasevar,paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))
writeToFile(tlogana3,paste(BetasavelogSig,hepiexts))
writeToFile(tlogana4,paste(BetasavelogSig,hepiexts))
writeToFile(" ",paste(BetasavelogSig,hepiexts))

}


#Overall signifcans of epistasis is determined in EpiCR. Varaince from EpiLW

signval<-EpiCR(trcontent,meantrait,trlength,sumcases,traittrim,vartrait,trait)
#No reason to calculate EpiLW if no significant epistasis is detected
#Implement this and maybe also HWE-test
genval<-EpiLW(traittrim,trmean,allFreq,sumcases)


##
for(ge1 in 1:numGenes){
	if(geneL[ge1]==gene1){
	   ge1ok<-ge1
	   break}
	}

##
for(ge2 in 1:numGenes){

	if(geneL[ge2]==gene2){
	ge2ok<-ge2
	break}
	}
##

#Beta-value gene1...
#if(as.numeric(signval[6])<epistsign){
if(as.numeric(signval[6])<SignMain){#NB Special sig-level for main effects
   mainBetaMatr[ge1ok,ge2ok]<<-as.numeric(signval[3])#has to be global, otherwise inserts are lost when returning to mainscript
   mainGene<-matrix(c(gname1,sval,trait),nrow=1)
   MainEffect<<-rbind(MainEffect,mainGene)
  }

#...and gene2
#if(as.numeric(signval[7])<epistsign){
if(as.numeric(signval[7])<SignMain){#NB Special sig-level for main effects
   mainBetaMatr[ge2ok,ge1ok]<<-as.numeric(signval[4]) 
   mainGene<-matrix(c(gname2,sval,trait),nrow=1)
   MainEffect<<-rbind(MainEffect,mainGene)
 }

#Additive variance in upper rigth triangle..
#if(as.numeric(signval[6])<epistsign || as.numeric(signval[7])<epistsign){
if(as.numeric(signval[6])<SignMain || as.numeric(signval[7])<SignMain){#NB Special sig-level for main effects
MainVarMatr[ge1ok,ge2ok]<<-as.numeric(genval[6])
#..and dominant variance in lower left triangle..
MainVarMatr[ge2ok,ge1ok]<<-as.numeric(genval[7])
  }

#Epistasis only of significant. NB Values are from EpiLW, and is tabulated disreagriding the Anova-values for beta.
if(as.numeric(signval[1])<epistsign || as.numeric(signval[2])<epistsign){
#Variances gene1 x gene2, epistasis
EpiBetaVarMatr[ge1ok,ge2ok]<<-as.numeric(genval[8])

#Beta-value gene1 x gene2, epistasis. NB If not possible to calculate from Anova, then set to zero
#Thus the mastirx may not be "symmetric" (variances always included, but not necessary beta-values. 
EpiBetaVarMatr[ge2ok,ge1ok]<<-as.numeric(signval[5])

#trlogsum contains sign-levels, relative amount of genetic varaince, and comments
#blogsum contains actual variances and betabalues
#NB Beta-values and add/dom variances should only be printed if significant (see above)

trlogsum<-matrix(c(eheadtrait2,gname1,gname2,signval[1],signval[2],genval[1:4],SnpMessage,aovNote),nrow=1)
blogsum<-matrix(c(sumcases,gname1,gname2,format(vartrait, digits = 3,nsmall=3),genval[5:8],signval[3:5]),nrow=1)
#eheadtrait2<-matrix(c(sval,format(meantrait, digits = 3,nsmall=2),format(vartrait, digits = 3,nsmall=2)),nrow=1)
##If above is done, then the if-statement not necessary, but the content is  
#if(as.numeric(signval[1])<epistsign || as.numeric(signval[2])<epistsign){

#Collate trlogsum
trlBind<<-rbind(trlBind,trlogsum)
#blogsum contains actual variances and betabalues
blogBind<<-rbind(blogBind,blogsum)

#writeToFile(trlogsum,paste(traitsavelogSig,hepiexts))
#writeToFile(blogsum,paste(BetasavelogSig,hepiexts))

#writeToFile(trlBind,paste(traitsavelogSig,hepiexts))
#writeToFile(blogBind,paste(BetasavelogSig,hepiexts))

#Updating counters
calcno<-calcno+1
#trnr<-trnr+1	
}
#else{#formetnlig overflødigNB NBNBNBmost probably not necessary
#trnr<-trnr+1	
#next
#}
#}# end of for(trt in trait1:trait2)


return(calcno)


}#function end
