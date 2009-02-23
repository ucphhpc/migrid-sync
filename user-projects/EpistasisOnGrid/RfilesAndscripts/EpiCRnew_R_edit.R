"EpiCR"<-function(trcontent=trcontent,meantrait,trlength,sumcases,traittrim1,allfreq,vartrait,eSave,htype,trait,acccrit){
#EPISTASIS	
#Physiological (Cheverud and Routman,1995), genotypic values used
#All genotypic values are obtained independently. Using these, variances (where appropiate) can be calculated using these
#avoiding covariances between derived genic or genotypic values.

#print(trcontent)
#Means of two-gene genotypes OK
mgAABB<-mean(trcontent[[1]],  na.rm=T)
mgAABb<-mean(trcontent[[2]],  na.rm=T)
mgAAbb<-mean(trcontent[[3]],  na.rm=T)
mgAaBB<-mean(trcontent[[4]],  na.rm=T)
mgAaBb<-mean(trcontent[[5]],  na.rm=T)
mgAabb<-mean(trcontent[[6]],  na.rm=T)
mgaaBB<-mean(trcontent[[7]],  na.rm=T)
mgaaBb<-mean(trcontent[[8]],  na.rm=T)
mgaabb<-mean(trcontent[[9]],  na.rm=T)

mgvect<-c(mgAABB,mgAABb,mgAAbb,mgAaBB,mgAaBb,mgAabb,mgaaBB,mgaaBb,mgaabb)
# Redit: for(mg in 1:9){if(mgvect[mg]=="NaN"){mgvect[mg] = 0}} # "=="-operator not applicable for comparing to NaN
for(mg in 1:9){if(is.nan(mgvect[mg])){mgvect[mg] = 0}}
                                                                                                   #print(warnings())                      
#Mean-corrected genotype means (deviation)
mgvectcor<-mgvect-meantrait
for(mg in 1:9){if(mgvect[mg]==0){mgvectcor[mg] = 0}}

#Variance of two-gene genotypes OK

#Redit: vgAABB<-var(trcontent[[1]],na.method="omit",unbiased=T)
#Redit: vgAABb<-var(trcontent[[2]],na.method="omit",unbiased=T)
#Redit: vgAAbb<-var(trcontent[[3]],na.method="omit",unbiased=T)
#Redit: vgAaBB<-var(trcontent[[4]],na.method="omit",unbiased=T)
#Redit: vgAaBb<-var(trcontent[[5]],na.method="omit",unbiased=T)
#Redit: vgAabb<-var(trcontent[[6]],na.method="omit",unbiased=T)
#Redit: vgaaBB<-var(trcontent[[7]],na.method="omit",unbiased=T)
#Redit: vgaaBb<-var(trcontent[[8]],na.method="omit",unbiased=T)
#Redit: vgaabb<-var(trcontent[[9]],na.method="omit",unbiased=T)

# function "var()" to be used in the following does not accept an empty vector argument, so we insert c(0) instead 
for(i in 1:length(trlength)){
  if(trlength[[i]] == 0){
    trcontent[[i]] = c(0)
  }
}

vgAABB<-var(trcontent[[1]],na.rm = TRUE)
vgAABb<-var(trcontent[[2]],na.rm = TRUE)
vgAAbb<-var(trcontent[[3]],na.rm = TRUE)
vgAaBB<-var(trcontent[[4]],na.rm = TRUE)
vgAaBb<-var(trcontent[[5]],na.rm = TRUE)
vgAabb<-var(trcontent[[6]],na.rm = TRUE)
vgaaBB<-var(trcontent[[7]],na.rm = TRUE)
vgaaBb<-var(trcontent[[8]],na.rm = TRUE)
vgaabb<-var(trcontent[[9]],na.rm = TRUE)

#print(trcontent[[1]])
                                                                                        
# maybe fix
#vgAABB<-var(trcontent[[1]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgAABb<-var(trcontent[[2]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgAAbb<-var(trcontent[[3]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgAaBB<-var(trcontent[[4]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgAaBb<-var(trcontent[[5]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgAabb<-var(trcontent[[6]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgaaBB<-var(trcontent[[7]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgaaBb<-var(trcontent[[8]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?
#vgaabb<-var(trcontent[[9]],na.rm=TRUE, use = "pairwise.complete.obs") # Korrekt?      
 
vgvect<-c(vgAABB,vgAABb,vgAAbb,vgAaBB,vgAaBb,vgAabb,vgaaBB,vgaaBb,vgaabb)

#print(vgvect)
#for(vg in 1:9){
#  print(is.nan(vgvect[vg]))
#  print(vgvect[vg]=="NA" || vgvect[vg]=="NaN")
#}
# Redit: for(vg in 1:9){if(vgvect[vg]=="NA" || vgvect[vg]=="NaN"){vgvect[vg] = 0}}
for(vg in 1:9){if(is.na(vgvect[vg]) || is.nan(vgvect[vg])){vgvect[vg] = 0}} # Kan ikke sammenligne NA (nonværdi) med "=="-operatoren
##t-values for genotypic values
#This just tests if the gentype means are different from the population mean
gentv<-abs(mgvectcor/sqrt(vgvect))#zero denominator results in "Inf" output. Removed below
for(ge in 1:9){if(vgvect[ge]==0){gentv[ge] = 0}}#pnorm below needs a value, but are removed in output

##p-values for epistatic values
genpv<-(1-pnorm(gentv))
for(ge in 1:9){if(vgvect[ge]==0){genpv[ge] = " "}}
#The above two could be combinde in one statement

#Average single-locus genotypic values as the average of two-gene genotypic values
gaverage<-sum(mgvect,na.rm=T)/9 #ONLY FOR GENOTYPES PRESENT?
#dif from meantrait

#Marginal single-locus genotypic values as the average of two-gene genotypic values OK
gAA<-sum(mgvect[1:3],na.rm=T)/3
gAa<-sum(mgvect[4:6],na.rm=T)/3
gaa<-sum(mgvect[7:9],na.rm=T)/3
gBB<-sum(mgvect[c(1,4,7)],na.rm=T)/3
gBb<-sum(mgvect[c(2,5,8)],na.rm=T)/3
gbb<-sum(mgvect[c(3,6,9)],na.rm=T)/3

##Non-epistatic genotypic values OK
neAABB<-gAA+gBB-gaverage
neAABb<-gAA+gBb-gaverage
neAAbb<-gAA+gbb-gaverage
neAaBB<-gAa+gBB-gaverage
neAaBb<-gAa+gBb-gaverage
neAabb<-gAa+gbb-gaverage
neaaBB<-gaa+gBB-gaverage
neaaBb<-gaa+gBb-gaverage
neaabb<-gaa+gbb-gaverage

nevect<-c(neAABB,neAABb,neAAbb,neAaBB,neAaBb,neAabb,neaaBB,neaaBb,neaabb)
#Exclude values for which there is no genotype values ie mgvect = 0
for(ng in 1:9){if(mgvect[ng]==0){nevect[ng] = 0}}

#Mean-corrected genotype means (deviation)
nevectcor<-nevect-gaverage
#Exclude values for which there is no genotype values ie nevect = 0
for(mg in 1:9){if(nevect[mg]==0){nevectcor[mg] = 0}}

#Variance of non-epistatic genotypes
#The above neijkl formulas are condensed, and variance is then calculated from the variances of the genotypic values
#CHECK Should these non-epi + epi var add to genotype var??
vneAABB<-(25*vgvect[1] + 4*(vgvect[2] + vgvect[3] + vgvect[4] + vgvect[7]) + vgvect[5] + vgvect[6] + vgvect[8] + vgvect[9])/81
vneAABb<-(25*vgvect[2] + 4*(vgvect[1] + vgvect[3] + vgvect[5] + vgvect[8]) + vgvect[4] + vgvect[6] + vgvect[7] + vgvect[9])/81
vneAAbb<-(25*vgvect[3] + 4*(vgvect[1] + vgvect[2] + vgvect[6] + vgvect[9]) + vgvect[4] + vgvect[5] + vgvect[7] + vgvect[8])/81
vneAaBB<-(25*vgvect[4] + 4*(vgvect[1] + vgvect[5] + vgvect[6] + vgvect[7]) + vgvect[2] + vgvect[3] + vgvect[8] + vgvect[9])/81
vneAaBb<-(25*vgvect[5] + 4*(vgvect[2] + vgvect[4] + vgvect[6] + vgvect[8]) + vgvect[1] + vgvect[3] + vgvect[7] + vgvect[9])/81
vneAabb<-(25*vgvect[6] + 4*(vgvect[3] + vgvect[4] + vgvect[5] + vgvect[9]) + vgvect[1] + vgvect[2] + vgvect[7] + vgvect[8])/81
vneaaBB<-(25*vgvect[7] + 4*(vgvect[1] + vgvect[4] + vgvect[8] + vgvect[9]) + vgvect[2] + vgvect[3] + vgvect[5] + vgvect[6])/81
vneaaBb<-(25*vgvect[8] + 4*(vgvect[2] + vgvect[5] + vgvect[7] + vgvect[9]) + vgvect[1] + vgvect[3] + vgvect[4] + vgvect[6])/81
vneaabb<-(25*vgvect[9] + 4*(vgvect[3] + vgvect[6] + vgvect[7] + vgvect[8]) + vgvect[1] + vgvect[2] + vgvect[4] + vgvect[5])/81

vnevect<-c(vneAABB,vneAABb,vneAAbb,vneAaBB,vneAaBb,vneAabb,vneaaBB,vneaaBb,vneaabb)
#Exclude for genotypes with less than two cases
for(ve in 1:9){if(trlength[ve]<2){vnevect[ve] = 0}}


##t-values for non-epistatic genotypic values
negentv<-abs(nevectcor/sqrt(vnevect))#zero denominator results in Inf output. Removed below
for(ge in 1:9){if(vnevect[ge]==0){negentv[ge] = 0}}#pnorm below needs a value, but are removed in output
##p-values for epistatic values
negenpv<-(1-pnorm(negentv))
for(ge in 1:9){if(vnevect[ge]==0){negenpv[ge] = " "}}

##
#Epistatic genotypic values OK
evect<-mgvect-nevect
#Exclude values for which there is no genotype values ie mgvect = 0
for(ng in 1:9){if(mgvect[ng]==0){evect[ng] = 0}}


#Variances of epistatic genotypic values
#Should be OK but check again
veAABB<-(16*vgvect[1] + 4*(vgvect[2] + vgvect[3] + vgvect[4] + vgvect[7]) + vgvect[5] + vgvect[6] + vgvect[8] + vgvect[9])/81
veAABb<-(16*vgvect[2] + 4*(vgvect[1] + vgvect[3] + vgvect[5] + vgvect[8]) + vgvect[4] + vgvect[6] + vgvect[7] + vgvect[9])/81
veAAbb<-(16*vgvect[3] + 4*(vgvect[1] + vgvect[2] + vgvect[6] + vgvect[9]) + vgvect[4] + vgvect[5] + vgvect[7] + vgvect[8])/81
veAaBB<-(16*vgvect[4] + 4*(vgvect[1] + vgvect[5] + vgvect[6] + vgvect[7]) + vgvect[2] + vgvect[3] + vgvect[8] + vgvect[9])/81
veAaBb<-(16*vgvect[5] + 4*(vgvect[2] + vgvect[4] + vgvect[6] + vgvect[8]) + vgvect[1] + vgvect[3] + vgvect[7] + vgvect[9])/81
veAabb<-(16*vgvect[6] + 4*(vgvect[3] + vgvect[4] + vgvect[5] + vgvect[9]) + vgvect[1] + vgvect[2] + vgvect[7] + vgvect[8])/81
veaaBB<-(16*vgvect[7] + 4*(vgvect[1] + vgvect[4] + vgvect[8] + vgvect[9]) + vgvect[2] + vgvect[3] + vgvect[5] + vgvect[6])/81
veaaBb<-(16*vgvect[8] + 4*(vgvect[2] + vgvect[5] + vgvect[7] + vgvect[9]) + vgvect[1] + vgvect[3] + vgvect[4] + vgvect[6])/81
veaabb<-(16*vgvect[9] + 4*(vgvect[3] + vgvect[6] + vgvect[7] + vgvect[8]) + vgvect[1] + vgvect[2] + vgvect[4] + vgvect[5])/81

vevect<-c(veAABB,veAABb,veAAbb,veAaBB,veAaBb,veAabb,veaaBB,veaaBb,veaabb)
for(ve in 1:9){if(trlength[ve]<2){vevect[ve] = 0}}

##t-values for epistatic values
epitv<-abs(evect/sqrt(vevect))#zero denominator results in Inf output. Removed below
for(ve in 1:9){if(vevect[ve]==0){epitv[ve] = 0}}#pnorm below needs a value, but are removed in output

##p-values for epistatic values
epipv<-(1-pnorm(epitv))
for(ve in 1:9){if(vevect[ve]==0){epipv[ve] = " "}}

######
#Significans of overall epistasis, F-test df=(4,n-9)

#There is a discrepancy in EMS between Cheverud et al 1995 and 1997.
#The 1997 formulation is probably the correct one. For the moment 1995 formulation is dropped from print

EMS<-sum(trlength*evect^2)/4
#In Cheverud 1995 the above bracket er substracte by SUM*SUM/N, where SUM is the sum of phenotypes across the entire population
#However this often results in negative epistasis mean square which is not possible.
#In addtion genotypic means has already been removed as the sum of epistais is zero.
#Besides, the sum-square term is not included in the 1997 paper. 


#RMS calculated as the sum of weigthed genotypic variance
RMS<-sum(vgvect*trlength)/sumcases
#It is stated just as the pooled variance, but it the above gives the same results as the ANOVA-design
#RMS<-sum(vgvect)
#The difference is huge!! but do not use. 

#RMS can be calculated as the residual mean square of two-way ANOVA with singel-locus genotypes and their interaction as factors
#aovRMS<-summary(aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim1, na.action=na.exclude))[4,3]
#However, the programs crasses when one of the genes are monogenic as the df=0 ie. no contrasts can be calculated.
#It appears although as the CR-calculation is valid. No sign discrepancies has been detected between the two calculations
#of significans.!!!!!!!!! Therefor DROP anova as it is cumbersome!

#   geneVector1 <- factor(as.character(traittrim1[, 1]))
#   geneVector2 <- factor(as.character(traittrim1[, 2]))
#	crosst<-table(geneVector1,geneVector2)

#NB hvis der kun er een værdi i en række eller kollonne, så falder aov da df=0!!

#Nemdfor koges bedre sammen
	crosst<-table(traittrim1[,1],traittrim1[,2])
	#print(crosst)
#print(dim(crosst))
if(dim(crosst)[1]<2){firstacc=0}
	else{firstacc=1}
if(dim(crosst)[2]<2){secondacc=0}
	else{secondacc=1}
	matacc<-firstacc+secondacc
#print(matacc)
#NBNBNBNBNB dim virker ikke helt da der kan være række (og kolonne formentlig) med 0 0 0, hvilket giver en dim. men er uden margnal værdi
#derfor skal der køres på dette også.
			
if(matacc<2){
	aovRMS<-"Monogenic"
Fval2<-" "
fpval2<-" "

}
else{
#print("value: "+traitVector~geneVector1+geneVector2 + geneVector1*geneVector2)

#print("traitvector")
#print(nlevels(traitVector ~ geneVector1+geneVector2 + geneVector1*geneVector2))
#print(traitVector)
#print(nlevels(traitVector))
#print(length(traitVector))
#print("genevector1")
#print(gname1)
#print(geneVector1)

#print(nlevels(geneVector1))
#print(length(geneVector1))
#print("genevector2")
#print(gname2)
#print(geneVector2)
#print(nlevels(geneVector2))

#print(length(geneVector2))
#print("traittrim1")
#print(traittrim1)
#print(length(traittrim1))
#aovobj <- aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim1, na.action=na.exclude)
#summa <- summary(aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim1, na.action=na.exclude))
#print(class(aovobj))
#sumdf <- summary.aov(aovobj)
#print(names(aovobj))
#print(class(sumdf))
#print(summa[[1]]["Mean Sq"])
#sumaschar <- as.character(summa)
#print(names(sumaschar))
#print(sumaschar["Mean Sq"])
#print(summa[[1,1]])
#print(names(aovobj))
#print(aovobj)
#print(summa)

#form <- as.formula(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2)

#hej <- lm(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2)
#print(hej)

#print(form)
#stop("hjase")
# Redit : aovRMS<-summary(aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim1, na.action=na.exclude))[4,3]

#contrasts(geneVector1, geneVector2)

#print("before aov")
op <- options(contrasts = c("contr.helmert", "contr.poly"))
#op <- options(contrasts = c("contr.helmert", "contr.treat"))
#traittrim1[36][1] = "ab"
#geneVector1[36] = "ab"
#print(class(traittrim1))
#print(traittrim1)
#geneVector2 <-  as.factor(c(6, 7))
#traittrim1 <- data.frame(c(1,2),c(3,4))
#print(geneVector1)
#aovmodel <- aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim1, na.action=na.exclude)
#print(paste(trait,gname1,gname2))

if(nlevels(geneVector1)>3 & nlevels(geneVector2) > 3){
#if(trait!="LDL" & gname1!="RHNF4A25" & gname2!="RHNF4A25"){
       
aovmodel <- aov(traitVector~geneVector1+geneVector2 + geneVector1+geneVector2+geneVector1:geneVector2, data=traittrim1, na.action=na.exclude)
#a+b+a:b
#aovmodel <- aov(traitVector~geneVector1, data=traittrim1, qr=F)
#traceback()
#print("before summary")
#aovRMS<-summary(aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim1, na.action=na.exclude))[[1]][4,3] # summary returns type c(summary.aov listof) in R. We need to access the summary.aov data (hence the indexing:"[[1]]")


aovRMS<-summary.aov(aovmodel)[[1]][4,3] # summary returns type c(summary.aov listof) in R. We need to access the summary.aov data (hence the indexing:"[[1]]")
}
else{aovRMS<-NA}

#print("after summary")
options(op)# reset to previous

#print(aovRMS)
# Redit : if(aovRMS=="NA"){ # "=="-operator not applicable when testing for NA
if(is.na(aovRMS)){
Fval2<-"RMS = 0"
fpval2<-1
}

else{

Fval2<-EMS/aovRMS
fpval2<-1-pf(Fval2, 4, (sumcases-9)) 
}
}
##

#fpval2<-"NA"
##clean up later i tabels etc. 

if(RMS==0){
Fval1<-"RMS = 0"
fpval1<-1
}
else{
Fval1<-EMS/RMS
fpval1<-1-pf(Fval1, 4, (sumcases-9)) 
}
#Output or signifcant values only
# Redit : if(fpval1=="NA"){fpval1=1} # "=="-operator not applicable when testing for NA
if(is.na(fpval1)){fpval1=1}
                                                                                       
# Redit : if(fpval2=="NA"){fpval2=1} # "=="-operator not applicable when testing for NA
if(is.na(fpval2)){fpval2=1}
                                                                                      
epioverall<-c(EMS,RMS,Fval1,fpval1,aovRMS,Fval2,fpval2)
######

#Single-locus genotypic values WITHOUT epistasis
addA<-abs(gAA - (gAA+gaa)/2)
domA<-gAa-(gAA+gaa)/2
addB<-abs(gBB - (gBB+gbb)/2)
domB<-gBb-(gBB+gbb)/2

#Epistatic genotypic values

eaa<-(evect[1] - evect[3] - evect[7] + evect[9])/4
ead<-(evect[6] - evect[4])/2
eda<-(evect[2] - evect[8])/2
edd<-evect[5]
adepi1<-c(addA, domA, addB, domB,eaa,ead,eda, edd)

#Variance of genotypic values and statistics
#Based on genotypic variances. For example:
#varaddA<-var((gAA-gaa)/2)=var(sum(mgvect[1:3],na.rm=T)/3-sum(mgvect[6:9],na.rm=T)/3)/2)=
#         (sum(vgvect[1:3])+sum(vgvect[6:9])/36

varaddA<-(vgvect[1] + vgvect[2] + vgvect[3] + vgvect[7] + vgvect[8] + vgvect[9])/36
vardomA<-(vgvect[4] + vgvect[5] + vgvect[6])/9 + varaddA
varaddB<-(vgvect[1] + vgvect[4] + vgvect[7] + vgvect[3] + vgvect[6] + vgvect[9])/36
vardomB<-(vgvect[2] + vgvect[5] + vgvect[8])/9 + varaddB

#and for specific epistatic genotypes, where specific genotype values are used.
#Some of 4.9 in Cheverud 2000 is not good!!
#To calculate the specific epi-variances the formulas for epistatic values has to be condensed (eaa,ead,eda.edd),although edd is a 
#singular term, that is no covariance is present and the dd-variance is simply the evect[5]. F.ex.:
#eAABB=neAABB-mgAABB<-(4*mgvect[1] - 2*(mgvect[2] + mgvect[3] + mgvect[4] + mgvect[7]) + mgvect[5] + mgvect[6] + mgvect[8] + mgvect[9])/9
#which exactly will give the genotypic epi-variances given in Cheverud 1995. 
#Epistatic values given from genotypic phenotypic values are(which is used for condensing-treatment, but not used else):

#eAABB<-(4*mgvect[1] - 2*(mgvect[2] + mgvect[3] + mgvect[4] + mgvect[7]) + mgvect[5] + mgvect[6] + mgvect[8] + mgvect[9])/9
#eAABb<-(4*mgvect[2] - 2*(mgvect[1] + mgvect[3] + mgvect[5] + mgvect[8]) + mgvect[4] + mgvect[6] + mgvect[7] + mgvect[9])/9
#eAAbb<-(4*mgvect[3] - 2*(mgvect[1] + mgvect[2] + mgvect[6] + mgvect[9]) + mgvect[4] + mgvect[5] + mgvect[7] + mgvect[8])/9
#eAaBB<-(4*mgvect[4] - 2*(mgvect[1] + mgvect[5] + mgvect[6] + mgvect[7]) + mgvect[2] + mgvect[3] + mgvect[8] + mgvect[9])/9
#eAaBb<-(4*mgvect[5] - 2*(mgvect[2] + mgvect[4] + mgvect[6] + mgvect[8]) + mgvect[1] + mgvect[3] + mgvect[7] + mgvect[9])/9
#eAabb<-(4*mgvect[6] - 2*(mgvect[3] + mgvect[4] + mgvect[5] + mgvect[9]) + mgvect[1] + mgvect[2] + mgvect[7] + mgvect[8])/9
#eaaBB<-(4*mgvect[7] - 2*(mgvect[1] + mgvect[4] + mgvect[8] + mgvect[9]) + mgvect[2] + mgvect[3] + mgvect[5] + mgvect[6])/9
#eaaBb<-(4*mgvect[8] - 2*(mgvect[2] + mgvect[5] + mgvect[7] + mgvect[9]) + mgvect[1] + mgvect[3] + mgvect[4] + mgvect[6])/9
#eaabb<-(4*mgvect[9] - 2*(mgvect[3] + mgvect[6] + mgvect[7] + mgvect[8]) + mgvect[1] + mgvect[2] + mgvect[4] + mgvect[5])/9

#ad and da in cheverud 2000 are interchanged, ad has wrong sign, and they should be divided by 6, not two.
#eaanew<-(mgvect[1] - mgvect[3] - mgvect[7] + mgvect[9])/4
#eadnew<-(2*mgvect[6] - mgvect[3] - 2*mgvect[4] - mgvect[9] + mgvect[1]+ mgvect[7])/6
#edanew<-(mgvect[9] + 2*mgvect[2] - mgvect[1] - mgvect[3] - 2*mgvect[8] + mgvect[7])/6
#These give the exact values as eaa,ead, and eda above

#Variances

vareaa<-(vgvect[1] + vgvect[3] + vgvect[7] + vgvect[9])/16
varead<-(4*vgvect[6] + vgvect[3] + 4*vgvect[4] + vgvect[9] + vgvect[1]+ vgvect[7])/36
vareda<-(vgvect[9] + 4*vgvect[2] + vgvect[1] + vgvect[3] + 4*vgvect[8] + vgvect[7])/36
varedd<-vevect[5]#OK

vargenADE<-c(varaddA,vardomA,varaddB,vardomB,vareaa,varead,vareda,varedd)

##t-values for genotypic values
genottv<-abs(adepi1/sqrt(vargenADE))
#print("inf check")
#print(vargenADE)
for(ve in 1:8){if(vargenADE[ve]=="Inf"){genottv[ve] = "NA"}}

##p-values for epistatic values
genotpv<-(1-pnorm(genottv))
#print(genottv)
######Population level GENIC values ie. allelic values and frequuency dependent

#Average population epistasis for single-locus genotypes
epiAA<-evect[1]*allfreq[3]^2 + 2*evect[2]*allfreq[3]*allfreq[4] + evect[3]*allfreq[4]^2
epiAa<-evect[4]*allfreq[3]^2 + 2*evect[5]*allfreq[3]*allfreq[4] + evect[6]*allfreq[4]^2
epiaa<-evect[7]*allfreq[3]^2 + 2*evect[8]*allfreq[3]*allfreq[4] + evect[9]*allfreq[4]^2
epiBB<-evect[1]*allfreq[1]^2 + 2*evect[4]*allfreq[1]*allfreq[2] + evect[7]*allfreq[2]^2
epiBb<-evect[2]*allfreq[1]^2 + 2*evect[5]*allfreq[1]*allfreq[2] + evect[8]*allfreq[2]^2
epibb<-evect[3]*allfreq[1]^2 + 2*evect[6]*allfreq[1]*allfreq[2] + evect[9]*allfreq[2]^2

##Single-locus genotypic values corrected for epistasis
addAe<-addA + (epiAA - epiaa)/2
domAe<-domA + (2*epiAa - epiAA -epiaa)/2
addBe<-addB + (epiBB - epibb)/2
domBe<-domB + (2*epiBb - epiBB -epibb)/2
adepi2<-c(addAe, domAe, addBe, domBe)

#Variances for Cheverud 1995 algor 18 and 19
#eAABB<-(4*mgvect[1] - 2*(mgvect[2] + mgvect[3] + mgvect[4] + mgvect[7]) + mgvect[5] + mgvect[6] + mgvect[8] + mgvect[9])/9
#eAABb<-(4*mgvect[2] - 2*(mgvect[1] + mgvect[3] + mgvect[5] + mgvect[8]) + mgvect[4] + mgvect[6] + mgvect[7] + mgvect[9])/9
#eAAbb<-(4*mgvect[3] - 2*(mgvect[1] + mgvect[2] + mgvect[6] + mgvect[9]) + mgvect[4] + mgvect[5] + mgvect[7] + mgvect[8])/9
#eAaBB<-(4*mgvect[4] - 2*(mgvect[1] + mgvect[5] + mgvect[6] + mgvect[7]) + mgvect[2] + mgvect[3] + mgvect[8] + mgvect[9])/9
#eAaBb<-(4*mgvect[5] - 2*(mgvect[2] + mgvect[4] + mgvect[6] + mgvect[8]) + mgvect[1] + mgvect[3] + mgvect[7] + mgvect[9])/9
#eAabb<-(4*mgvect[6] - 2*(mgvect[3] + mgvect[4] + mgvect[5] + mgvect[9]) + mgvect[1] + mgvect[2] + mgvect[7] + mgvect[8])/9
#eaaBB<-(4*mgvect[7] - 2*(mgvect[1] + mgvect[4] + mgvect[8] + mgvect[9]) + mgvect[2] + mgvect[3] + mgvect[5] + mgvect[6])/9
#eaaBb<-(4*mgvect[8] - 2*(mgvect[2] + mgvect[5] + mgvect[7] + mgvect[9]) + mgvect[1] + mgvect[3] + mgvect[4] + mgvect[6])/9
#eaabb<-(4*mgvect[9] - 2*(mgvect[3] + mgvect[6] + mgvect[7] + mgvect[8]) + mgvect[1] + mgvect[2] + mgvect[4] + mgvect[5])/9

q1<-3*allfreq[3]^2
q2<-6*(allfreq[3]*allfreq[4])
q3<-3*allfreq[4]^2
p1<-3*allfreq[1]^2
p2<-6*(allfreq[1]*allfreq[2])
p3<-3*allfreq[2]^2

varaddAe<-((3 - q2 - q3)^2*(vgvect[1]- vgvect[7]) + (3 - q1 - q3)^2*(vgvect[2]- vgvect[8]) + (3 - q1 - q2)^2*(vgvect[3]- vgvect[9]))/36

vardomAe<-((2 - q2 - q3)^2*(vgvect[1] + vgvect[7]) + (2 - q1 - q3)^2*(vgvect[2] + vgvect[8]) + (2 - q1 - q2)^2*(vgvect[3]+vgvect[9])+
			(2 - 2*q1)^2*4*vgvect[4] + (2 - 2*q2)^2*4*vgvect[5] + (2 - 2*q3)^2*4*vgvect[6])/36

varaddBe<-((3 - p2 - p3)^2*(vgvect[1]- vgvect[3]) + (3 - p1 - p3)^2*(vgvect[4]- vgvect[6]) + (3 - p1 - p2)^2*(vgvect[7]- vgvect[9]))/36

vardomBe<-((2 - p2 - p3)^2*(vgvect[1] + vgvect[3]) + (2 - p1 - p3)^2*(vgvect[4] + vgvect[6]) + (2 - p1 - p2)^2*(vgvect[7] + vgvect[9])+
			(2 - 2*p1)^2*4*vgvect[2] + (2 - 2*p2)^2*4*vgvect[5] + (2 - 2*p3)^2*4*vgvect[8])/36

varADcorE<-c(varaddAe,vardomAe,varaddBe,vardomBe)

##t-values for additive and dominant effects including epistasis
varADcorEtv<-abs(adepi2/sqrt(varADcorE))
for(ve in 1:4){if(varADcorE[ve]=="Inf"){varADcorEtv[ve] = "NA"}}

##p-values for epistatic values
varADcorEpv<-(1-pnorm(varADcorEtv))

#Total epigenic values
epiaver<-allfreq[1]^2*allfreq[3]^2*evect[1] + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*evect[2] + allfreq[1]^2*allfreq[4]^2*evect[3] +
		 2*allfreq[1]*allfreq[2]*allfreq[3]^2*evect[4] + 4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*evect[5] + 
		 2*allfreq[1]*allfreq[2]*allfreq[4]^2*evect[6] + allfreq[2]^2*allfreq[3]^2*evect[7] +2*allfreq[2]^2*allfreq[3]*allfreq[4]*evect[8] +
		allfreq[2]^2*allfreq[4]^2*evect[9]

#Average effect of allels

avA1<-allfreq[2]*(addA + domA*(allfreq[2] - allfreq[1])) + allfreq[1]*allfreq[2]*(epiAA-epiAa) + allfreq[2]^2*(epiAa - epiaa)
avA2<-(-allfreq[1])*(addA + domA*(allfreq[2] - allfreq[1])) + allfreq[1]*allfreq[2]*(epiaa-epiAa) + allfreq[1]^2*(epiAa - epiAA)
avAs<- addA + domA*(allfreq[2] - allfreq[1]) + allfreq[1]*(epiAA-epiAa) + allfreq[2]*(epiAa - epiaa)
avB1<-allfreq[4]*(addB + domB*(allfreq[4] - allfreq[3])) + allfreq[3]*allfreq[4]*(epiBB-epiBb) + allfreq[4]^2*(epiBb - epibb)
avB2<-(-allfreq[3])*(addB + domB*(allfreq[4] - allfreq[3])) + allfreq[3]*allfreq[4]*(epibb-epiBb) + allfreq[3]^2*(epiBb - epiBB)
avBs<-addB + domB*(allfreq[4] - allfreq[3]) + allfreq[3]*(epiBB-epiBb) + allfreq[4]*(epiBb - epibb)

aveffhead2<-c(gname1,"","",gname2)
aveff<-c(avA1,avA2,avAs,avB1,avB2,avBs)

#her med dominans hvor 12 er den væsentlige
domA12<-2*allfreq[1]*allfreq[2]*domA - allfreq[1]*allfreq[2]*(epiAA - 2*epiAa + epiaa)
domB12<-2*allfreq[3]*allfreq[4]*domB - allfreq[3]*allfreq[4]*(epiBB - 2*epiBb + epibb)

aveff<-c(avA1,avA2,avAs,domA12,avB1,avB2,avBs,domB12,epiaver)

#Variances

varavaddA<-2*allfreq[1]*allfreq[2]*avAs^2
varavaddB<- 2*allfreq[3]*allfreq[4]*avBs^2
varavdomA<-(allfreq[1]^2*allfreq[2]^2*(2*domA - epiAA + 2*epiAa - epiaa))^2 
varavdomB<- (allfreq[3]^2*allfreq[4]^2*(2*domB - epiBB + 2*epiBb - epibb))^2

#varint<-sum(trlength*(ivect^2))/9
totgenvar<-varavaddA + varavaddB + varavdomA + varavdomB
vargenot<-c("Variances:",vartrait,varavaddA,varavaddB,varavdomA,varavdomB,totgenvar)
varFval<-c("t-value:","",abs(aveff[3]/sqrt(varavaddA)),abs(aveff[7]/sqrt(varavaddB)),abs(aveff[4]/sqrt(varavdomA)),abs(aveff[8]/sqrt(varavdomB)))

# Redit : varPval<-c("P-values","",1-pnorm(varFval[3]),1-pnorm(varFval[4]),1-pnorm(varFval[5]),1-pnorm(varFval[6]))
varPval<-c("P-values","",1-pnorm(as.numeric(varFval[3])),1-pnorm(as.numeric(varFval[4])),1-pnorm(as.numeric(varFval[5])),1-pnorm(as.numeric(varFval[6]))) # the functions pnorm does not accept a non-numeric argument

heravv<-c("Heritabilities:","",varavaddA/vartrait,varavaddB/vartrait,varavdomA/vartrait,varavdomB/vartrait,totgenvar/vartrait)

#Output CR

#Cheverud and Routman

	writeToFile(matrix(c("","","Cheverud and Routman decomposition"), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Physiological decomposition"), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))

	writeToFile(matrix(c("","","Overall significance of epistatis:"), nrow=1), paste(eSave, epiext,sep=""))
	ftest1<-c("","Genotypic RMS","","","ANOVA RMS")
	ftest2<-c("EMS","RMS","F-value","p-value","RMS","F-value","p-value")
	writeToFile(matrix(c("","","",ftest1), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",ftest2), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",epioverall), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))

	writeToFile(matrix(c("","","Haplotype:","",htype), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Number of cases:","",trlength), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Genotypic value:","",mgvect), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Genotypic deviation:","",mgvectcor), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Genotypic variance:","",vgvect), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Genotypic t-value:","",gentv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Genotypic p-value:","",genpv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Nonepistatic value:","",nevect), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Nonepistatic deviation:","",nevectcor), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Nonepistatic variance:","",vnevect), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Nonepistatic t-value:","",negentv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Nonepistatic p-value:","",negenpv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Epistatic value:","",evect), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Epistatic variance:","",vevect), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Epistatic t-value:","",epitv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Epistatic p-value:","",epipv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))

	slad2<-c("Genotypic values:","","",gname1,"",gname2)
	slad3<-c("","","Additive","Dominant","Additive","Dominant","eAA","eAD","eDA","eDD")
	writeToFile(matrix(c("","",slad2), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",slad3), nrow=1), paste(eSave, epiext,sep=""))
	adepi1head<-c("Without epistasis","")

	writeToFile(matrix(c("","",adepi1head,adepi1), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Variance:","",vargenADE), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","t-value:","",genottv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","p-value","",genotpv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Including epistasis","",adepi2), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Variance:","",varADcorE), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","t-value:","",varADcorEtv), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","p-value:","",varADcorEpv), nrow=1), paste(eSave, epiext,sep=""))

	writeToFile("", paste(eSave, epiext,sep=""))
	aveffhead1<-c("Average effects (population values)")
	aveffhead3<-c("Allel A","Allel a", "Allel subst.","DomAa","Allel B","Allel b","Allel subst.","DomBb","Epistasis")
	writeToFile(matrix(c("","",aveffhead1), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",aveffhead2), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",aveffhead3), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",aveff), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))
	varhead<-c("Total variance","AdditiveA","AdditiveB","DominantA","DominantB","Total genetic var")

	writeToFile(matrix(c("","","",varhead), nrow=1), paste(eSave, epiext,sep=""))	
	writeToFile(matrix(c("","",vargenot), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",varFval), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",varPval), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",heravv), nrow=1), paste(eSave, epiext,sep=""))
	


#Indicate as default non-significance for print in Log trait
fpvalue12<-"F"

#Printing of traits significant/non-sig
traitsignif<-0

#if(fpval1<epistsign || fpval2<epistsign){
#	slad4<-c("","","Additive A","Dominant A","Additive B","Dominant B","eAA","eAD","eDA","eDD")
esheadtrait2<-matrix(c(sval,Fval1,fpval1,Fval2,fpval2),nrow=1)
 #   write.table(esheadtrait2,paste(esSave,epiexts,sep=""),sep="\t",append=T)
#    write.table(" ",paste(esSave,epiexts,sep=""),sep="\t",append=T)
#	write.table(matrix(c("","","","","CR Genotypic p-values",slad4), nrow=1), paste(esSave, epiexts,sep=""), sep = "\t", append = T)
#	write.table(matrix(c("","","","","","Without epistasis","",genotpv), nrow=1), paste(esSave, epiexts,sep=""), sep = "\t", append = T)
#	write.table(matrix(c("","","","","","Including epistasis","",varADcorEpv), nrow=1), paste(esSave, epiexts,sep=""), sep = "\t", append = T)
   
   #Indicate if significance is present for print in Log trait
#	fpvalue12<-"T"
	#Printing of significant traits 
#	traitsignif<-names(smplt[c(trait)])#change to value =1, with list-headings in output?
   
#}#end summary output
#else{esheadtrait2=c(sval,gname1,gname2,"","ns","","ns")}
signpval<-c(fpval1,fpval2,traitsignif,esheadtrait2,fpvalue12)#NB esheadtrait2 contains 5 elements;fpval1 is doubled!ÆNdRES til det nødvendige
return(signpval)

}
