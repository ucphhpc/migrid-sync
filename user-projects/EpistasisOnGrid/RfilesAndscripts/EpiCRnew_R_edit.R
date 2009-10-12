"EpiCR"<-function(trcontent=trcontent,meantrait,trlength,sumcases,traittrim,vartrait,trait){
#EPISTASIS	
#Physiological (Cheverud and Routman,1995), genotypic values used
#All genotypic values are obtained independently. Using these, variances (where appropiate) can be calculated using these
#avoiding covariances between derived genic or genotypic values.

#print("In EpiCR")

#Below means and varaince is calculated for each two-gene haplotype. Can this be doen in a single less
#costly procedure???


#Means of two-gene genotypes OK Mayb droped and instead use mean from t-test!
#This is the geontypic values!!
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

#Calculating variance
# function "var()" to be used in the following does not accept an empty vector argument,
#so we insert c(0) instead 
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
 
vgvect<-c(vgAABB,vgAABb,vgAAbb,vgAaBB,vgAaBb,vgAabb,vgaaBB,vgaaBb,vgaabb)
for(vg in 1:9){if(is.na(vgvect[vg]) || is.nan(vgvect[vg])){vgvect[vg] = 0}} # Kan ikke sammenligne NA (nonværdi) med "=="-operatoren

#Average single-locus genotypic values as the average of two-gene genotypic values
gaverage<-sum(mgvect,na.rm=T)/9 #ONLY FOR GENOTYPES PRESENT? Philosophical question

#Calculation ofnon-epistasis values. 

#Marginal single-locus genotypic values as the average of two-gene genotypic values OK
#these are intermediate calculations
gAA<-sum(mgvect[1:3],na.rm=T)/3
gAa<-sum(mgvect[4:6],na.rm=T)/3
gaa<-sum(mgvect[7:9],na.rm=T)/3
gBB<-sum(mgvect[c(1,4,7)],na.rm=T)/3
gBb<-sum(mgvect[c(2,5,8)],na.rm=T)/3
gbb<-sum(mgvect[c(3,6,9)],na.rm=T)/3

#Are used to calculate single genotype values

##Mean non-epistatic genotypic values OK
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

##Epistatic genotypic values OK
evect<-mgvect-nevect

#Exclude values for which there is no genotype values ie mgvect = 0
for(ng in 1:9){if(mgvect[ng]==0){evect[ng] = 0}}

######
#Significans of overall epistasis, F-test df=(4,n-9)

#There is a discrepancy in EMS between Cheverud et al 1995 and 1997.
#The 1997 formulation is probably the correct one. For the moment 1995 formulation is dropped from print

EMS<-sum(trlength*evect^2)/4
#In Cheverud 1995 the above bracket er substracte by SUM*SUM/N, where SUM is the sum of phenotypes across the entire population
#However this sum is zero as all calculation have been zero-centered
#Besides, the sum-square term is not included in the 1997 paper. 

#Two residuals are calculated. We may drop one of them.
#RMS calculated as the sum of weigthed genotypic variance

RMS<-sum(vgvect*trlength)/sumcases #DROP???
#It is stated just as the pooled variance, but the above gives approximately the same results as the ANOVA-design

#RMS can be calculated as the residual mean square of two-way ANOVA with singel-locus genotypes and their interaction as factors
#It appears although as the CR-calculation is valid. No sign discrepancies has been detected between the two calculations
#Entries are the names of the columns in traittrim OK

#Mean squares
aovX<-summary(aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim, na.action=na.exclude))[[1]]


#Beta-parameters, extendt to single genes too

aovY<-aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim, na.action=na.exclude)[[1]]
BetaVal<-aovY[2:4]#this may be done global, be sure not to "carry-over"

BetaValues<-c(format(BetaVal[1],digits=3,nsmall=3),format(BetaVal[2],digits=3,nsmall=3),format(BetaVal[3],digits=3,nsmall=3))

if(BetaValues[3]=="NA"){BetaValues[3]<-0}

#P-values for main effects
MainGene1Sign<-aovX[1,5]
MainGene2Sign<-aovX[2,5]

#Extract RMS
if(dim(aovX)[1]==4){
   aovRMS<-aovX[4,3]
   aovNote<<-""}
   else{
	if(dim(aovX)[1]==3){
	aovRMS<-aovX[3,3]
       	 aovNote<<-"No AnoEpi"
	}
	else{
	aovNote<<-"Invalid"
	aovRMS<-"NA"
#This be superflous, but keep to debugging is complete
print("in epiberegn")
print(aovX)
print(gene1)
print(gene2)
print(gname1)
print(gname2)
print(dim(aovX))

	}

}
#The result of two RMS-calcualtions are nearly identical
#To handel zero-valued RMS's and NA and NaN

if(aovRMS==0 || aovRMS== "NA" || aovRMS== "NaN"){

print("i aovRMS = NA")
print(aovRMS)
MainGene1Sign<-1
MainGene2Sign<-1

Fval2<-"RMS = 0"
fpval2<-1
}
else{
Fval2<-EMS/aovRMS
fpval2<-1-pf(Fval2, 4, (sumcases-9)) 

if(fpval2 == "NA" || fpval2 == "NaN"){fpval2<-1

	}
   else{fpval2<-format(fpval2, digits = 4,scientific=T)}
}

if(RMS==0){
Fval1<-"RMS = 0"
fpval1<-1
}
else{
Fval1<-EMS/RMS
fpval1<-1-pf(Fval1, 4, (sumcases-9)) 
if(fpval1 == "NA" || fpval1 == "NaN"){fpval1<-1}
    else{fpval1<-format(fpval1, digits = 4,scientific=T)}
}
                                                                           
######

#No further calculations here, but see older scripts for variances etc.

signpval<-c(fpval1,fpval2,BetaValues,MainGene1Sign,MainGene2Sign)

return(signpval)

}
