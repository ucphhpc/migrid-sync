#Revised by MF 18.march 2009 
#

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

for(traitn in traits){
     #print(paste("trait ",trait))
     #if(trait=="LDL"){
       
     #}

  trait<-names(smplt[c(traitn)])
  
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

#Can the above be done in instead of tw procedures?????

#Create a cross-table of two-gene counts to test for valid input for further calculations.
#A full table has 3x3 entries as each SNP (mutation, polymorphism) has three values: aa, ab, and bb
#The table is used ensure valid entries into the next calculations. Basically, this means that none of
#the two genes must be monomorphic e.g. only aa. 
#The entries in the table are not used anymore, except for the above purpose (however see below).
#Would it be more economical to use the union-function in C or C++ e.g union(gene1) and skip if the size =1??
#The procedure to only process genes witha at least two values e.g. aa and ab, is mandatory for two reaosns:
#epistasis do not have any meaning for monomorphic genes, and aov breaks down

crosst<-table(traittrim[,1],traittrim[,2])

#Check for monomorphic genes and to secure validity of ANOVA(aov)
#aov fails if only one row or one column has entries different from zeros
if(dim(crosst)[1]==1){next}
if(dim(crosst)[1]==2){
	a1<-sum(crosst[1,])
	a2<-sum(crosst[2,])
	if(a1==0 || a2==0){next}	
}
if(dim(crosst)[1]==3){
	a1<-sum(crosst[1,])
	a2<-sum(crosst[2,])
	a3<-sum(crosst[3,])
	if((a1==0 & a2==0) || (a1==0 & a3==0) || (a2==0 & a3==0))
	{next}	
}
if(dim(crosst)[2]==1){next}
if(dim(crosst)[2]==2){
	b1<-sum(crosst[,1])
	b2<-sum(crosst[,2])
	if(b1==0 || b2==0){next}	
}
if(dim(crosst)[2]==3){
	b1<-sum(crosst[,1])
	b2<-sum(crosst[,2])
	b3<-sum(crosst[,3])
	if((b1==0 & b2==0) || (b1==0 & b3==0) || (b2==0 & b3==0))
	{next}	
}

#first and second moments of the trait in the popultion; maybe one procedure??
#Trait mean 
meantrait<-mean(traittrim[3])#NB This is grand mean

#Trait variance
   #Redit: vartrait<-var(traittrim[4],unbiased=T)[1]
   vartrait<-var(traittrim[3])[1] # "...unbiased arguement unused..."
     # alternative #vartrait<-var(traittrim[4], na.rm=TRUE, use = "pairwise.complete.obs")[1] # Umiddelbart den indstilling der virkede. Korrekt??
##CHECK var komandoen i R: Unbiased at der divideres med N-1, dvs sample var, men division med N betyder populations var

#Output sval = selcted class;
eheadtrait2<-matrix(c(sval,meantrait,vartrait),nrow=1)


##############

#Selection of cases according to haplotype. Non-valid traits excluded. 
#The actual traitvalues are included, not the mean-corrected.OK!!
#Can this be done by using the cross-tab above??I think however, that the cpu-time may not
#be reduced, but the benefit is that other types of gene-variations may be included, particular
#microsatelites witch may have 10 or more values. This is not an issue right now, the issue is to 
#reduce computing time

gdfAABB<-traittrim[(traittrim[1]=="aa" & traittrim[2]=="aa"),3]
gdfAABb<-traittrim[(traittrim[1]=="aa" & traittrim[2]=="ab"),3]
gdfAAbb<-traittrim[(traittrim[1]=="aa" & traittrim[2]=="bb"),3]
gdfAaBB<-traittrim[(traittrim[1]=="ab" & traittrim[2]=="aa"),3]
gdfAaBb<-traittrim[(traittrim[1]=="ab" & traittrim[2]=="ab"),3]
gdfAabb<-traittrim[(traittrim[1]=="ab" & traittrim[2]=="bb"),3]
gdfaaBB<-traittrim[(traittrim[1]=="bb" & traittrim[2]=="aa"),3]
gdfaaBb<-traittrim[(traittrim[1]=="bb" & traittrim[2]=="ab"),3]
gdfaabb<-traittrim[(traittrim[1]=="bb" & traittrim[2]=="bb"),3]

#number of haplotypes
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
#trcontent list all the values for each two-gene haplotype, which is exported to EpiCR.


#Number of cases
sumcases<-sum(trlength)


################

#Headings for outputs
#Necesary to do here, as traits are accessed succesively in this script, not in main script
traitsavelogSig<-paste("Log trait epistasis ",names(smplt[c(selectvar)]),trait) 
tlogana1<-matrix(c("EPISTASIS calculations."),nrow=1)
tlogana2<-matrix(c("Only haplotypes with significant epistasis of the trait are printed."),nrow=1)
tlogana3<-matrix(c("Significance level:","","",epistsign),nrow=1)
tlogfile<-matrix(c("File:","","",fileimp),nrow=1)
tloghead1<-matrix(c("Classification variable:","","",names(smplt[c(selectvar)])),nrow=1)
trheadtrait<-matrix(c("Trait:"," ","",trait),nrow=1)
tloghead2<-matrix(c("Number of classes:","","",levmax),nrow=1)
tloghead3<-matrix(c("Number of genes:","","",numgene),nrow=1)
tupdates1<-matrix(c("","","","","","","","","", "Significant epistasis"),nrow=1)
tupdates2<-matrix(c("Class","Mean","","","Total variance","","Gene 1","Gene 2", "pCR", "pAnova"),nrow=1)

#MF comment eventually cut HWE and Haplotype stat if it consumes time!Interesting stuff but may be calculated separately for positiv epi-pairs

if(lognum==0){
#kun overskrifter een gang

#summary signifcant only
#This file only contains the bonferoni corrected significant epistasis.
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
writeToFile(tloghead2,paste(traitsavelogSig,hepiexts))
writeToFile(tloghead3,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tlogana3,paste(traitsavelogSig,hepiexts))
writeToFile(" ",paste(traitsavelogSig,hepiexts))
writeToFile(tupdates1,paste(traitsavelogSig,hepiexts))
writeToFile(tupdates2,paste(traitsavelogSig,hepiexts))

}


#Overall signifcans of epistasis is determined in EpiCR
signval<-EpiCR(trcontent,meantrait,trlength,sumcases,traittrim,vartrait,trait)


trlogsum<-matrix(c(eheadtrait2,gname1,gname2,signval),nrow=1)

##
if(as.numeric(signval[1])<epistsign || as.numeric(signval[2])<epistsign){
writeToFile(trlogsum,paste(traitsavelogSig,hepiexts))
#Updating counters
calcno<-calcno+1
trnr<-trnr+1	
}
else{#formetnlig overflødigNB NBNBNBmost probably not necessary
trnr<-trnr+1	
next}
}# end of for(trt in trait1:trait2)


return(calcno)


}#function end
