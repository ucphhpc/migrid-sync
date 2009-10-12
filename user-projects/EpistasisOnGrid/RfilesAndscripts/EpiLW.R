#Created 21. May 2009

"EpiLW"<-function(traittrim,trmean,allFreq,sumcases){


###Lynch and Walsh 1998

#print("In EpiLW")
#Mean values

expdata<-trmean
allFreq<-allFreq
sumcases<-sumcases

#Genotypic vlaues

gVaacc<-allFreq[1]*allFreq[1]*allFreq[3]*allFreq[3]*expdata[1]
gVaacd<-2*allFreq[1]*allFreq[1]*allFreq[3]*allFreq[4]*expdata[2]
gVaadd<-allFreq[1]*allFreq[1]*allFreq[4]*allFreq[4]*expdata[3]
gVabcc<-2*allFreq[1]*allFreq[2]*allFreq[3]*allFreq[3]*expdata[4]
gVabcd<-4*allFreq[1]*allFreq[2]*allFreq[3]*allFreq[4]*expdata[5]
gVabdd<-2*allFreq[1]*allFreq[2]*allFreq[4]*allFreq[4]*expdata[6]
gVbbcc<-allFreq[2]*allFreq[2]*allFreq[3]*allFreq[3]*expdata[7]
gVbbcd<-2*allFreq[2]*allFreq[2]*allFreq[3]*allFreq[4]*expdata[8]
gVbbdd<-allFreq[2]*allFreq[2]*allFreq[4]*allFreq[4]*expdata[9]

gValues<-c(gVaacc,gVaacd,gVaadd,gVabcc,gVabcd,gVabdd,gVbbcc,gVbbcd,gVbbdd)

#Weigthed genotypic value, all
TotgValues<-sum(gValues, na.rm = T)

#Additive effect conditional on ech allel

#1) genotypic means
#Allele A
gmaacc<-allFreq[1]*allFreq[3]*allFreq[3]*expdata[1]
gmaacd<-2*allFreq[1]*allFreq[3]*allFreq[4]*expdata[2]
gmaadd<-allFreq[1]*allFreq[4]*allFreq[4]*expdata[3]
gmabcc<-allFreq[2]*allFreq[3]*allFreq[3]*expdata[4]
gmabcd<-2*allFreq[2]*allFreq[3]*allFreq[4]*expdata[5]
gmabdd<-allFreq[2]*allFreq[4]*allFreq[4]*expdata[6]

addGa<-sum(c(gmaacc,gmaacd,gmaadd,gmabcc,gmabcd,gmabdd),na.rm = T)

#Allel B
gmabcc<-allFreq[1]*allFreq[3]*allFreq[3]*expdata[4]
gmabcd<-2*allFreq[1]*allFreq[3]*allFreq[4]*expdata[5]
gmabdd<-allFreq[1]*allFreq[4]*allFreq[4]*expdata[6]
gmbbcc<-allFreq[2]*allFreq[3]*allFreq[3]*expdata[7]
gmbbcd<-2*allFreq[2]*allFreq[3]*allFreq[4]*expdata[8]
gmbbdd<-allFreq[2]*allFreq[4]*allFreq[4]*expdata[9]

addGb<-sum(c(gmabcc,gmabcd,gmabdd,gmbbcc,gmbbcd,gmbbdd),na.rm = T)

#Allel C
gmaacc<-allFreq[1]*allFreq[1]*allFreq[3]*expdata[1]
gmabcc<-2*allFreq[1]*allFreq[2]*allFreq[3]*expdata[4]
gmbbcc<-allFreq[2]*allFreq[2]*allFreq[3]*expdata[7]
gmaacd<-allFreq[1]*allFreq[1]*allFreq[4]*expdata[2]
gmabcd<-2*allFreq[1]*allFreq[2]*allFreq[4]*expdata[5]
gmbbcd<-allFreq[2]*allFreq[2]*allFreq[4]*expdata[8]

addGc<-sum(c(gmaacc,gmabcc,gmbbcc,gmaacd,gmabcd,gmbbcd),na.rm = T)

#Allel D
gmaacd<-allFreq[1]*allFreq[1]*allFreq[3]*expdata[2]
gmabcd<-2*allFreq[1]*allFreq[2]*allFreq[3]*expdata[5]
gmbbcd<-allFreq[2]*allFreq[2]*allFreq[3]*expdata[8]
gmaadd<-allFreq[1]*allFreq[1]*allFreq[4]*expdata[3]
gmabdd<-2*allFreq[1]*allFreq[2]*allFreq[4]*expdata[6]
gmbbdd<-allFreq[2]*allFreq[2]*allFreq[4]*expdata[9]

addGd<-sum(c(gmaacd,gmabcd,gmbbcd,gmaadd,gmabdd,gmbbdd),na.rm = T)

#Additive effects

addEffa<-addGa - TotgValues
addEffb<-addGb - TotgValues
addEffc<-addGc - TotgValues
addEffd<-addGd - TotgValues

#Additive variance

AddVarGene1<-2*(allFreq[1]*addEffa*addEffa + allFreq[2]*addEffb*addEffb)
AddVarGene2<-2*(allFreq[3]*addEffc*addEffc + allFreq[4]*addEffd*addEffd)

#Total additive variance

AddVarTot<-AddVarGene1 + AddVarGene2

##Dominant value, effects and variance

#Conditonal genotypic values

gVaa<-allFreq[3]*allFreq[3]*expdata[1] + 2*allFreq[3]*allFreq[4]*expdata[2] + allFreq[4]*allFreq[4]*expdata[3]
gVab<-allFreq[3]*allFreq[3]*expdata[4] + 2*allFreq[3]*allFreq[4]*expdata[5] + allFreq[4]*allFreq[4]*expdata[6]
gVbb<-allFreq[3]*allFreq[3]*expdata[7] + 2*allFreq[3]*allFreq[4]*expdata[8] + allFreq[4]*allFreq[4]*expdata[9]
gVcc<-allFreq[1]*allFreq[1]*expdata[1] + 2*allFreq[1]*allFreq[2]*expdata[4] + allFreq[2]*allFreq[2]*expdata[7]
gVcd<-allFreq[1]*allFreq[1]*expdata[2] + 2*allFreq[1]*allFreq[2]*expdata[5] + allFreq[2]*allFreq[2]*expdata[8]
gVdd<-allFreq[1]*allFreq[1]*expdata[3] + 2*allFreq[1]*allFreq[2]*expdata[6] + allFreq[2]*allFreq[2]*expdata[9]

#Dominant effects

domEffaa<-gVaa - TotgValues - addEffa - addEffa 
domEffab<-gVab - TotgValues - addEffa - addEffb 
domEffbb<-gVbb - TotgValues - addEffb - addEffb 
domEffcc<-gVcc - TotgValues - addEffc - addEffc 
domEffcd<-gVcd - TotgValues - addEffc - addEffd 
domEffdd<-gVdd - TotgValues - addEffd - addEffd 

#Dominant variance
domVaraa<- allFreq[1]*allFreq[1]*domEffaa*domEffaa
domVarab<- 2*allFreq[1]*allFreq[2]*domEffab*domEffab
domVarbb<- allFreq[2]*allFreq[2]*domEffbb*domEffbb
domVarcc<- allFreq[3]*allFreq[3]*domEffcc*domEffcc
domVarcd<- 2*allFreq[3]*allFreq[4]*domEffcd*domEffcd
domVardd<- allFreq[4]*allFreq[4]*domEffdd*domEffdd

domVarTot<-sum(c(domVaraa,domVarab,domVarbb,domVarcc,domVarcd,domVardd),na.rm = T)

#Phenotypic variance


PhenVar<-sum(c(
allFreq[1]*allFreq[1]*allFreq[3]*allFreq[3]*expdata[1]*expdata[1],
2*allFreq[1]*allFreq[1]*allFreq[3]*allFreq[4]*expdata[2]*expdata[2], 
allFreq[1]*allFreq[1]*allFreq[4]*allFreq[4]*expdata[3]*expdata[3],
2*allFreq[1]*allFreq[2]*allFreq[3]*allFreq[3]*expdata[4]*expdata[4],
4*allFreq[1]*allFreq[2]*allFreq[3]*allFreq[4]*expdata[5]*expdata[5],
2*allFreq[1]*allFreq[2]*allFreq[4]*allFreq[4]*expdata[6]*expdata[6],
allFreq[2]*allFreq[2]*allFreq[3]*allFreq[3]*expdata[7]*expdata[7],
2*allFreq[2]*allFreq[2]*allFreq[3]*allFreq[4]*expdata[8]*expdata[8],
allFreq[2]*allFreq[2]*allFreq[4]*allFreq[4]*expdata[9]*expdata[9]),na.rm = T)

GeneVarTot<-PhenVar - TotgValues*TotgValues

EpiVarTot<-GeneVarTot - AddVarTot - domVarTot

GeneV<-format(GeneVarTot/PhenVar,digits=4,scientific = TRUE)
AddV<-format(AddVarTot/GeneVarTot,digits=4,scientific = TRUE)
DomV<-format(domVarTot/GeneVarTot,digits=4,scientific = TRUE)
EpiV<-format(EpiVarTot/GeneVarTot,digits=4,scientific = TRUE)
###

GenVar<-c(GeneV,AddV,DomV,EpiV,format(GeneVarTot,digits=3,nsmall=3),format(AddVarTot,digits=3,nsmall=3),format(domVarTot,digits=3,nsmall=3),format(EpiVarTot,digits=3,nsmall=3))
#her overføres også de facto værdier
return(GenVar)
}# end function
