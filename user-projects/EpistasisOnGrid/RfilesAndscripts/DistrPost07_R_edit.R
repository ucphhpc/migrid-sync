#UDVILKLING Summariske tabeller skal være mere overskuelige. Formentlig vil df-fil være OK,
#med passende spørgsmåls-dialog
#beregning af fraktion af epistasis er i forhold til mulige når moinogene er udelukket.
#bør være mod antal potentielle interaktioner dvs gen*(gen-1). eller begge dele.
#der er en pæn discrepans mellem Var-decom og SS i pak-sham beregningerne
#Når der ikke er sign epistasis for en klasse udskrives denne ikke. Bør udskrives med None e.lign.
#Faktisk bør alt vel udskrives og først efterfølgende bør der sorteres på baggrund af valgt significans.

"DistrPost"<-function()
{

#Priming list for significant traits
# benja edit : trait2 and trait1 no longer present
 # traitlist<-rep(0,abs(trait2-trait1+1))
  traitlist<-rep(0,length(traits))
  trnr<-1

# Benja edit: trait indexes are no longer used. Instead traits are in the "traits" vector .
#for(trt in trait1:trait2)
 # {traitch<-trt #Omvej nødvendig for at få navn og ikke nummer i output (vistnok)
                #der skal importeres som en data-frame, se EpiEval mm

#   trait<-names(smplt[c(traitch)])

for(trait in traits){
     #print(paste("trait ",trait))
     #if(trait=="LDL"){
       
     #}
     # Redit : traitVector <- as.numeric(smpl[, c(trait)])

  traitVector <<- as.numeric(smpl[, c(trait)]) # we need to make traitVector global ("<<-" instead of "<-")

  
  qtrait<-data.frame(geneVector1,geneVector2,traitVector)
  dimdf<-dim(qtrait)
   
#Delete all missing variables

#print(length(qtrait[,1]))
# Redit: traittrimpre<-as.data.frame(qtrait[(qtrait[1] !='NA' & qtrait[2] !='NA' & qtrait[3] !=misvt),(1:3)]) 
traittrimpre<-as.data.frame(qtrait[(!is.na(qtrait[1]) & !is.na(qtrait[2]) & qtrait[3] !=misvt),(1:3)]) # cannot use "!=" operator for 'NA'

  
# Redit : traittrim<-as.data.frame(traittrimpre[(traittrimpre[1] !='NA' & traittrimpre[2] !='NA' & traittrimpre[3] !='NA'),(1:3)])
traittrim<-as.data.frame(traittrimpre[(!is.na(traittrimpre[1]) & !is.na(traittrimpre[2]) & !is.na(traittrimpre[3])),(1:3)]) # cannot use "!=" operator for 'NA'
                                        #print("traittrim:")

                                       #Trait mean

  
meantrait<-mean(traittrim[3])

#This is the working data frame. Variables are centered! NB necessary??Variance should be the same irrespective of centering
#Also, meantrait should only be used as a population value. It is not the weighted genotypic mean!!
     traittrim1<-cbind(traittrim,(traittrim[3]-meantrait))

#Indsæt crosstab til at se om dim er mindre end 2 for både rækker og kolloner! Hvis så, da skip! og next
#Pt flyttes det til to-vejs anova for ikke at komme i kambolage med div tabel-opdateringer.


#Trait variance
   #Redit: vartrait<-var(traittrim1[4],unbiased=T)[1]
   vartrait<-var(traittrim1[4])[1] # "...unbiased arguement unused..."
     # alternative #vartrait<-var(traittrim1[4], na.rm=TRUE, use = "pairwise.complete.obs")[1] # Umiddelbart den indstilling der virkede. Korrekt??

#Epistasis output: general table, compile all data for each two-genes, all classes CR and PS

eSave<-paste("Epistasis",names(smplt[c(selectvar)]),trait, gname1,"-",gname2) 
etitel<-matrix(c("EPISTASIS"),nrow=1)
eheadfile<-matrix(c("File:","",fileimp),nrow=1)
eheadclvar<-matrix(c("Classification variable:"," ",names(smplt[c(selectvar)])),nrow=1)
eheadgene<-matrix(c("Gene A:",gname1,"Gene B:",gname2),nrow=1)
eheadtrait<-matrix(c("Trait:"," ",trait),nrow=1)

# Benja note : strengen "paste(eSave,epiext,sep="")" er filnavnet
   
if(tblnum==0){#kun overskrifter een gang nbnb VIRKER IKKE HELT. hVAD MED if.exist elign.
#General
writeToFile(" ",paste(eSave,epiext,sep=""))
writeToFile(etitel,paste(eSave,epiext,sep=""))
writeToFile(" ",paste(eSave,epiext,sep=""))
writeToFile(date(),paste(eSave,epiext,sep=""))
writeToFile(" ",paste(eSave,epiext,sep=""))
writeToFile(eheadfile,paste(eSave,epiext,sep=""))
writeToFile(" ",paste(eSave,epiext,sep=""))
writeToFile(eheadclvar,paste(eSave,epiext,sep=""))
writeToFile(" ",paste(eSave,epiext,sep=""))
writeToFile(eheadtrait,paste(eSave,epiext,sep=""))
writeToFile(" ",paste(eSave,epiext,sep=""))
writeToFile(eheadgene,paste(eSave,epiext,sep=""))
writeToFile(" ",paste(eSave,epiext,sep=""))

}

##############
#Selection of cases according to haplotype. Non-valid traits excluded. 
#The actual traitvalues are included, not the mean-corrected.OK!!
#for(tsel in 1:dimdf[1]){
gdfAABB<-traittrim1[(traittrim1[1]=="aa" & traittrim1[2]=="aa"),3]
gdfAABb<-traittrim1[(traittrim1[1]=="aa" & traittrim1[2]=="ab"),3]
gdfAAbb<-traittrim1[(traittrim1[1]=="aa" & traittrim1[2]=="bb"),3]
gdfAaBB<-traittrim1[(traittrim1[1]=="ab" & traittrim1[2]=="aa"),3]
gdfAaBb<-traittrim1[(traittrim1[1]=="ab" & traittrim1[2]=="ab"),3]
gdfAabb<-traittrim1[(traittrim1[1]=="ab" & traittrim1[2]=="bb"),3]
gdfaaBB<-traittrim1[(traittrim1[1]=="bb" & traittrim1[2]=="aa"),3]
gdfaaBb<-traittrim1[(traittrim1[1]=="bb" & traittrim1[2]=="ab"),3]
gdfaabb<-traittrim1[(traittrim1[1]=="bb" & traittrim1[2]=="bb"),3]
#}

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

htype<-c("AABB","AABb","AAbb","AaBB","AaBb","Aabb","aaBB","aaBb","aabb")


#Number of cases
sumcases<-sum(trlength)

AAgeno<-ltr1 + ltr2 + ltr3
Aageno<-ltr4 + ltr5 + ltr6
aageno<-ltr7 + ltr8 + ltr9
BBgeno<-ltr1 + ltr4 + ltr7
Bbgeno<-ltr2 + ltr5 + ltr8
bbgeno<-ltr3 + ltr6 + ltr9
allelA<-(2*sum(AAgeno) + sum(Aageno))/(2*sumcases)
allela<-(2*sum(aageno) + sum(Aageno))/(2*sumcases)
allelB<-(2*sum(BBgeno) + sum(Bbgeno))/(2*sumcases)
allelb<-(2*sum(bbgeno) + sum(Bbgeno))/(2*sumcases)

#Dette er counts EFTER missing traits er deleted! Delete og inkorp her!allfreq ORDET BRUGES I Epi-scripts
allfreq<-matrix(as.numeric(c(allelA,allela,allelB,allelb)),nrow=1)

GenoTypes<-matrix(c("aa","ab","bb"),nrow=1)

#Dette er counts EFTER missing traits er deleted.
GenoCounts<-matrix(as.numeric(c(AAgeno,Aageno,aageno,BBgeno,Bbgeno,bbgeno)),nrow=1)

#Gene1 OK
HWEtest1<-HWEwigNew(sumcases,GenoCounts[1],GenoCounts[2],GenoCounts[3])
#Gene2 OK
HWEtest2<-HWEwigNew(sumcases,GenoCounts[4],GenoCounts[5],GenoCounts[6])

#Haplotype OK
GenoChi<-chisq.test(matrix(trlength,3,3))$p.value


#Headings

#Epistasis output: summary; compile genotypes, haplotypes, hwe, ld, and epi sign, PS vardecomp
#in one line for each two-gene combination. 
#The txt-version is the WORKING FILE FOPR ALL SUCCESIVE EVALUATIONS.
traitcont<-paste(nselvar,trait,sep="") 
traitsavelog<-paste("Log trait epistasis",names(smplt[c(selectvar)]),trait) 
traitsavelogSig<-paste("Log trait epistasis Sign.",names(smplt[c(selectvar)]),trait) 
tlogana1<-matrix(c("HERITABILITIES AND EPISTASIS."),nrow=1)
tlogana2<-matrix(c("Only haplotypes with significant epistasis of the trait are printed."),nrow=1)
tlogana2a<-matrix(c("Monogenic genotypes are not included."),nrow=1)
tlogana3<-matrix(c("Significance level:","",epistsign),nrow=1)
tlogfile<-matrix(c("File:","",fileimp),nrow=1)
tloghead1<-matrix(c("Classification variable:","",names(smplt[c(selectvar)])),nrow=1)
tloghead2<-matrix(c("Number of classes:","",levmax),nrow=1)
tloghead3<-matrix(c("Number of genes:","",numgene),nrow=1)
trheadtrait<-matrix(c("Trait:"," ",trait),nrow=1)
tupdates1<-matrix(c("","","","Genotypes Gene1","","","","Genotypes Gene2","","","","","Haplotypes","","","","","","","","",
					 "Significant epistasis", "", "","","PS variance extended","","","","","","","PS var. extended actual","","","","","","",
					"PS SS-variance decomposition","","","","PS SS-var. actual"),nrow=1)
tupdates2<-matrix(c("Class","Gene 1","Gene 2", GenoTypes,"pG1", GenoTypes,"pG2",htype,"pLD", "F-CR", "pCR", "F-Anova","pAnova",
			"Total genetic variance","Additive","Dominance","Add-Add","Add-Dom","Dom-Dom","Epistasis",
			"Total genetic variance","Additive","Dominance","Add-Add","Add-Dom","Dom-Dom","Epistasis",
			"Total genetic variance","Additive","Dominance","Epistasis",
			"Total genetic variance","Additive","Dominance","Epistasis"),nrow=1)

if(lognum==0){
#kun overskrifter een gang

#Output to evaluations,txt-file
writeToFile(tupdates2,paste(traitcont,evalext,sep=""))

#summary
writeToFile(" ",paste(traitsavelog,hepiexts))
writeToFile(tlogana1,paste(traitsavelog,hepiexts))
writeToFile(tlogana2a,paste(traitsavelog,hepiexts))
writeToFile(" ",paste(traitsavelog,hepiexts))
writeToFile(date(),paste(traitsavelog,hepiexts))
writeToFile(" ",paste(traitsavelog,hepiexts))
writeToFile(tlogfile,paste(traitsavelog,hepiexts))
writeToFile(" ",paste(traitsavelog,hepiexts))
writeToFile(tloghead1,paste(traitsavelog,hepiexts))
writeToFile(" ",paste(traitsavelog,hepiexts))
writeToFile(trheadtrait,paste(traitsavelog,hepiexts))
writeToFile(" ",paste(traitsavelog,hepiexts))
writeToFile(tloghead2,paste(traitsavelog,hepiexts))
writeToFile(tloghead3,paste(traitsavelog,hepiexts))
writeToFile(" ",paste(traitsavelog,hepiexts))
writeToFile(tupdates1,paste(traitsavelog,hepiexts))
writeToFile(tupdates2,paste(traitsavelog,hepiexts))

#summary signifcant only
#This file only contains the bonferoni correctedsignificant epistasis.
#This is later selected in epieval from the major file above. Drop this??
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tlogana1,paste(traitsavelogSig,hepiexts))
writeToFile(tlogana2,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(date(),paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tlogfile,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tloghead1,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(trheadtrait,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tlogana3,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tloghead2,paste(traitsavelogSig,hepiexts))
writeToFile(tloghead3,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tupdates1,paste(traitsavelogSig,hepiexts))
writeToFile(tupdates2,paste(traitsavelogSig,hepiexts))

}

#fortsæt uden overskrifter
eheadtrait1<-matrix(c("Class","Mean","Variance"),nrow=1)
eheadtrait2<-matrix(c(sval,meantrait,vartrait),nrow=1)
esheadtrait1<-matrix(c("Class","Gene A","Gene B","Trait","F-CR","pCR","F-Anova","pAnova"),nrow=1)
esheadsign<-matrix(c("Significance level","",epistsign), nrow=1)
     
writeToFile(eheadtrait1,paste(eSave,epiext,sep=""))
writeToFile(eheadtrait2,paste(eSave,epiext,sep=""))
writeToFile(" ",paste(eSave,epiext,sep=""))


#print("before EpiCR")
#Overall signifcans of epistasis is determined in EpiCR
signval<-EpiCR(trcontent,meantrait,trlength,sumcases,traittrim1,allfreq,vartrait,eSave,htype,trait,acccrit)
#print("before EpiPS")
heritPS<-EpiPS(traittrim1,allfreq,vartrait,trlength,eSave,esSave)

#Save summary epistatic data, general	
trlogsum<-matrix(c(signval[4],gname1,gname2,GenoCounts[1:3],HWEtest1[1],GenoCounts[4:6],HWEtest1[2], trlength, GenoChi,
			signval[5:8],heritPS[1:22]),nrow=1)
writeToFile(trlogsum,paste(traitsavelog,hepiexts))
writeToFile(trlogsum,paste(traitcont,evalext,sep=""))


if(as.numeric(signval[1])<epistsign){
writeToFile(trlogsum,paste(traitsavelogSig,hepiexts))}

traitlist[trnr]<-signval[3]
#bruges ikke pt, da det også skal omformuleres. Koster ikke noget pt.
trnr<-trnr+1	
}# end of for(trt in trait1:trait2)

return(traitlist)

}#function end
