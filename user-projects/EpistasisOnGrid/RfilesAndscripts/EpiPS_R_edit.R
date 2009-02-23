"EpiPS"<-function(traittrim1,allfreq,vartrait,trlength,eSave,esSave){

###Sham,P "Statistics in human genetics" 1998
#All calculations are done with genotypic values as deviations from overall mean. Cases with missing genotypes and traitvalue is excluded


#Udvikling: single droppes til fordel for Falconer i heritability. Burde være ens, men check (og så kan det være at den bevares)
#Der er mindre forskelle i dom og epistasis (og derfro mellem total) mellem SS- og V-beregningerne. Formler er checket, men re-check
#Efter forleøbig check er der forskel mellem de to evalueringer.
#Elaborer beregninger foretaget med counts i stedet for allel-frekvenser.

#Single locus genotypic deviations from overall mean (entrance [4])

dgAA<-mean(traittrim1[traittrim1[1]=="aa",4]) 
dgAa<-mean(traittrim1[traittrim1[1]=="ab",4]) 
dgaa<-mean(traittrim1[traittrim1[1]=="bb",4]) 
dgBB<-mean(traittrim1[traittrim1[2]=="aa",4]) 
dgBb<-mean(traittrim1[traittrim1[2]=="ab",4]) 
dgbb<-mean(traittrim1[traittrim1[2]=="bb",4]) 

#Number of cases
ldgAA<-length(traittrim1[traittrim1[1]=="aa",4])
ldgAa<-length(traittrim1[traittrim1[1]=="ab",4])
ldgaa<-length(traittrim1[traittrim1[1]=="bb",4])
ldgBB<-length(traittrim1[traittrim1[2]=="aa",4])
ldgBb<-length(traittrim1[traittrim1[2]=="ab",4])
ldgbb<-length(traittrim1[traittrim1[2]=="bb",4])

dglength<-c(ldgAA,ldgAa,ldgaa,ldgBB,ldgBb,ldgbb)

#Correction for mean ==NA, as this command is not honoured;se smarter methods with a for statement
	if(dglength[1]==0){dgAA<-0}
	if(dglength[2]==0){dgAa<-0}
	if(dglength[3]==0){dgaa<-0}
	if(dglength[4]==0){dgBB<-0}
	if(dglength[5]==0){dgBb<-0}
	if(dglength[6]==0){dgbb<-0}
		
#Additive genic effects 5.21

smyA<-allfreq[1]*dgAA + allfreq[2]*dgAa
smya<-allfreq[1]*dgAa + allfreq[2]*dgaa
smyB<-allfreq[3]*dgBB + allfreq[4]*dgBb
smyb<-allfreq[3]*dgBb + allfreq[4]*dgbb

#Dominant genic effects 5.18

sdAA<-dgAA - 2*smyA
sdAa<-dgAa - smyA - smya
sdaa<-dgaa - 2*smya
sdBB<-dgBB - 2*smyB
sdBb<-dgBb - smyB- smyb
sdbb<-dgbb - 2*smyb

sgeneffect<-c(smyA,smya,sdAA,sdAa,sdaa,smyB,smyb,sdBB,sdBb,sdbb)

#Single locus variance decomposition 5.19 (dom) and 5.23(add). 5.20 and 5.22 is flawed

slAVA<-2*allfreq[1]*allfreq[2]*(allfreq[1]*(dgAA - dgAa) + allfreq[2]*(dgAa -dgaa))^2   
slAVD<-allfreq[1]^2*sdAA^2 +2*allfreq[1]*allfreq[2]*sdAa^2 +allfreq[2]^2*sdaa^2
slAVG<-allfreq[1]^2*dgAA^2 + 2*allfreq[1]*allfreq[2]*dgAa^2 + allfreq[2]^2*dgaa^2
slBVA<-2*allfreq[3]*allfreq[4]*(allfreq[3]*(dgBB - dgBb) + allfreq[4]*(dgBb -dgbb))^2   
slBVD<-allfreq[3]^2*sdBB^2 +2*allfreq[3]*allfreq[4]*sdBb^2 +allfreq[4]^2*sdbb^2
slBVG<-allfreq[3]^2*dgBB^2 + 2*allfreq[3]*allfreq[4]*dgBb^2 + allfreq[4]^2*dgbb^2

varADG<-c(vartrait,slAVA,slAVD,slAVG,slBVA,slBVD,slBVG)

#Single locus Heritabilities
herADG<-c(slAVA/vartrait,slAVD/vartrait,slAVG/vartrait,slBVA/vartrait,slBVD/vartrait,slBVG/vartrait)

##Two-locus model; epistasis
#HWE and LE assumed

#Marginal means, all defined as deviations from overall mean, i.e. the traittrim1 data frame[4] is used

#Four allels ("un-corrected" DD interaction)
mAABB<-mean(traittrim1[traittrim1[1]=="aa" & traittrim1[2]=="aa",4]) 
mAABb<-mean(traittrim1[traittrim1[1]=="aa" & traittrim1[2]=="ab",4]) 
mAAbb<-mean(traittrim1[traittrim1[1]=="aa" & traittrim1[2]=="bb",4]) 
mAaBB<-mean(traittrim1[traittrim1[1]=="ab" & traittrim1[2]=="aa",4]) 
mAaBb<-mean(traittrim1[traittrim1[1]=="ab" & traittrim1[2]=="ab",4]) 
mAabb<-mean(traittrim1[traittrim1[1]=="ab" & traittrim1[2]=="bb",4]) 
maaBB<-mean(traittrim1[traittrim1[1]=="bb" & traittrim1[2]=="aa",4]) 
maaBb<-mean(traittrim1[traittrim1[1]=="bb" & traittrim1[2]=="ab",4]) 
maabb<-mean(traittrim1[traittrim1[1]=="bb" & traittrim1[2]=="bb",4]) 

#Correction for no cases
#se epi-script for smarter solution
	if(trlength[1]==0){mAABB<-0}
	if(trlength[2]==0){mAABb<-0}
	if(trlength[3]==0){mAAbb<-0}
	if(trlength[4]==0){mAaBB<-0}
	if(trlength[5]==0){mAaBb<-0}
	if(trlength[6]==0){mAabb<-0}
	if(trlength[7]==0){maaBB<-0}
	if(trlength[8]==0){maaBb<-0}
	if(trlength[9]==0){maabb<-0}

#Three alleles 5.28. Sum genotype frequences * genotype value ("un-corrected" AD interaction)

mAABy<-allfreq[3]*mAABB + allfreq[4]*mAABb
mAAby<-allfreq[3]*mAABb + allfreq[4]*mAAbb
mAaBy<-allfreq[3]*mAaBB + allfreq[4]*mAaBb
mAaby<-allfreq[3]*mAaBb + allfreq[4]*mAabb
maaBy<-allfreq[3]*maaBB + allfreq[4]*maaBb
maaby<-allfreq[3]*maaBb + allfreq[4]*maabb
mAxBB<-allfreq[1]*mAABB + allfreq[2]*mAaBB
maxBB<-allfreq[1]*mAaBB + allfreq[2]*maaBB
mAxBb<-allfreq[1]*mAABb + allfreq[2]*mAaBb
maxBb<-allfreq[1]*mAaBb + allfreq[2]*maaBb
mAxbb<-allfreq[1]*mAAbb + allfreq[2]*mAabb
maxbb<-allfreq[1]*mAabb + allfreq[2]*maabb

#Two alleles 5.29. Sum genotype frequences * genotype value ("un-corrected" AA interaction)

mAxBy<-allfreq[1]*allfreq[3]*mAABB + allfreq[2]*allfreq[3]*mAaBB + allfreq[1]*allfreq[4]*mAABb + allfreq[2]*allfreq[4]*mAaBb 
mAxby<-allfreq[1]*allfreq[3]*mAABb + allfreq[1]*allfreq[4]*mAAbb + allfreq[2]*allfreq[3]*mAaBb + allfreq[2]*allfreq[4]*mAabb 
maxBy<-allfreq[1]*allfreq[3]*mAaBB + allfreq[1]*allfreq[4]*mAaBb + allfreq[2]*allfreq[3]*maaBB + allfreq[2]*allfreq[4]*maaBb 
maxby<-allfreq[1]*allfreq[3]*mAaBb + allfreq[1]*allfreq[4]*mAabb + allfreq[2]*allfreq[3]*maaBb + allfreq[2]*allfreq[4]*maabb 

#Two alleles 5.24. Sum genotype frequences * genotype value ("un-corrected" dominans)

mAAyy<-allfreq[3]^2*mAABB + 2*allfreq[3]*allfreq[4]*mAABb + allfreq[4]^2*mAAbb
mAayy<-allfreq[3]^2*mAaBB + 2*allfreq[3]*allfreq[4]*mAaBb + allfreq[4]^2*mAabb
maayy<-allfreq[3]^2*maaBB + 2*allfreq[3]*allfreq[4]*maaBb + allfreq[4]^2*maabb
mxxBB<-allfreq[1]^2*mAABB + 2*allfreq[1]*allfreq[2]*mAaBB + allfreq[2]^2*maaBB
mxxBb<-allfreq[1]^2*mAABb + 2*allfreq[1]*allfreq[2]*mAaBb + allfreq[2]^2*maaBb
mxxbb<-allfreq[1]^2*mAAbb + 2*allfreq[1]*allfreq[2]*mAabb + allfreq[2]^2*maabb

#GENIC effect. 5.25 Check!!

tmyA<-allfreq[1]*mAAyy + allfreq[2]*mAayy
tmya<-allfreq[1]*mAayy + allfreq[2]*maayy
tmyB<-allfreq[3]*mxxBB + allfreq[4]*mxxBb
tmyb<-allfreq[3]*mxxBb + allfreq[4]*mxxbb

tgeneff<-c("",tmyA,tmya,tmyB,tmyb)

#DOMINANCE interaction

tmyAA<-mAAyy - 2*tmyA
tmyAa<-mAayy - tmyA - tmya
tmyaa<-maayy - 2*tmya
tmyBB<-mxxBB - 2*tmyB
tmyBb<-mxxBb - tmyB -tmyb
tmybb<-mxxbb - 2*tmyb

tdomeff<-c("",tmyAA,tmyAa,tmyaa,tmyBB,tmyBb,tmybb)

#ADDITIVE-ADDITIVE interaction

tmyAB<-mAxBy - tmyA - tmyB
tmyAb<-mAxby - tmyA - tmyb
tmyaB<-maxBy - tmya - tmyB
tmyab<-maxby - tmya - tmyb

tAAeff<-c("",tmyAB,tmyAb,tmyaB,tmyab)

#ADDITIVE-DOMINANCE interaction
#		mean     dom    AddAdd        Genic 
tmyAAB<-mAABy - tmyAA -2*tmyAB - 2*tmyA - tmyB
tmyAAb<-mAAby - tmyAA -2*tmyAb - 2*tmyA - tmyb
tmyAaB<-mAaBy - tmyAa -tmyAB - tmyaB - tmyA - tmya - tmyB
tmyAab<-mAaby - tmyAa -tmyAb - tmyab - tmyA - tmya - tmyb
tmyaaB<-maaBy - tmyaa - 2*tmyaB - 2*tmya - tmyB
tmyaab<-maaby - tmyaa - 2*tmyab - 2*tmya - tmyb

tmyABB<-mAxBB - tmyBB -2*tmyAB - tmyA - 2*tmyB
tmyaBB<-maxBB - tmyBB -2*tmyaB - tmya - 2*tmyB
tmyABb<-mAxBb - tmyBb -tmyAB - tmyAb - tmyA - tmyB - tmyb
tmyaBb<-maxBb - tmyBb -tmyaB - tmyab - tmya - tmyB - tmyb
tmyAbb<-mAxbb - tmybb -2*tmyAb - tmyA - 2*tmyb
tmyabb<-maxbb - tmybb -2*tmyab - tmya - 2*tmyb

tADeff<-c("",tmyAAB,tmyAAb,tmyAaB,tmyAab,tmyaaB,tmyaab,tmyABB,tmyaBB,tmyABb,tmyaBb,tmyAbb,tmyabb)

#DOMINANCE-DOMINANCE interaction
#		  mean     Add-dom                    	    AddAdd          						dom              Genic 
tmyAABB<-mAABB - 2*tmyAAB - 2*tmyABB          	- 4*tmyAB            					- tmyAA -tmyBB - 2*tmyA - 2*tmyB
tmyAABb<-mAABb - tmyAAB - tmyAAb - 2*tmyABb   	- 2*tmyAB - 2*tmyAb  					- tmyAA -tmyBb - 2*tmyA - tmyB - tmyb
tmyAAbb<-mAAbb - 2*tmyAAb - 2*tmyAbb          	- 4*tmyAb              					- tmyAA -tmybb - 2*tmyA - 2*tmyb

tmyAaBB<-mAaBB - tmyABB - tmyaBB - 2*tmyAaB   	- 2*tmyAB - 2*tmyaB  					- tmyAa -tmyBB - tmyA - tmya - 2*tmyB
tmyAaBb<-mAaBb - tmyAaB -tmyAab -tmyABb -tmyaBb - tmyAB - tmyaB - tmyAb - tmyab 		- tmyAa -tmyBb - tmyA - tmya - tmyB - tmyb
tmyAabb<-mAabb - 2*tmyAab - tmyAbb - tmyabb     - 2*tmyAb - 2*tmyab   					- tmyAa -tmybb - tmyA - tmya - 2*tmyb

tmyaaBB<-maaBB - 2*tmyaaB - 2*tmyaBB          	- 4*tmyaB            					- tmyaa -tmyBB - 2*tmya - 2*tmyB
tmyaaBb<-maaBb - tmyaaB - tmyaab - 2*tmyaBb   	- 2*tmyaB - 2*tmyab 						- tmyaa -tmyBb - 2*tmya - tmyB - tmyb
tmyaabb<-maabb - 2*tmyaab - 2*tmyabb          	- 4*tmyab             					- tmyaa -tmybb - 2*tmya - 2*tmyb

tDDeff<-c("",tmyAABB,tmyAABb,tmyAAbb,tmyAaBB,tmyAaBb,tmyAabb,tmyaaBB,tmyaaBb,tmyaabb)

#Additive genic variance, VA
tlVA<-allfreq[1]^2*allfreq[3]^2*(2*tmyA + 2*tmyB)^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*(2*tmyA + tmyB + tmyb)^2 +
	   allfreq[1]^2*allfreq[4]^2*(2*tmyA + 2*tmyb)^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*(tmyA + tmya + 2*tmyB)^2 +
		4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*(tmyA + tmya + tmyB + tmyb)^2 +
	   2*allfreq[1]*allfreq[2]*allfreq[4]^2*(tmyA + tmya + 2*tmyb)^2 + allfreq[2]^2*allfreq[3]^2*(2*tmya + 2*tmyB)^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*(2*tmya + tmyB + tmyb)^2 + allfreq[2]^2*allfreq[4]^2*(2*tmya + 2*tmyb)^2

#Dominance variance, VD
tlVD<-allfreq[1]^2*allfreq[3]^2*(tmyAA + tmyBB)^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*(tmyAA + tmyBb)^2 +
	   allfreq[1]^2*allfreq[4]^2*(tmyAA + tmybb)^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*(tmyAa + tmyBB)^2 +
		4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*(tmyAa + tmyBb)^2 +
	   2*allfreq[1]*allfreq[2]*allfreq[4]^2*(tmyAa + tmybb)^2 + allfreq[2]^2*allfreq[3]^2*(tmyaa + tmyBB)^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*(tmyaa + tmyBb)^2 + allfreq[2]^2*allfreq[4]^2*(tmyaa + tmybb)^2

#Additive-Additive variance, VAA
tlVAA<-allfreq[1]^2*allfreq[3]^2*(4*tmyAB)^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*(2*tmyAB + 2*tmyAb)^2 +
	   allfreq[1]^2*allfreq[4]^2*(4*tmyAb)^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*(2*tmyAB + 2*tmyaB)^2 +
		4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*(tmyAB + tmyAb + tmyaB + tmyab)^2 +
	   2*allfreq[1]*allfreq[2]*allfreq[4]^2*(2*tmyAb + 2*tmyab)^2 + allfreq[2]^2*allfreq[3]^2*(4*tmyaB)^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*(2*tmyaB + 2*tmyab)^2 + allfreq[2]^2*allfreq[4]^2*(4*tmyab)^2

#Additive-dominance variance, VAD
tlVAD<-allfreq[1]^2*allfreq[3]^2*(2*tmyAAB + 2*tmyABB)^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*(2*tmyABb + tmyAAB + tmyAAb)^2 +
	   allfreq[1]^2*allfreq[4]^2*(2*tmyAAb + 2*tmyAbb)^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*(2*tmyAaB + tmyABB + tmyaBB)^2 +
		4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*(tmyAaB + tmyAab + tmyABb + tmyaBb)^2 +
	   2*allfreq[1]*allfreq[2]*allfreq[4]^2*(2*tmyAab + tmyAbb + tmyabb)^2 + allfreq[2]^2*allfreq[3]^2*(2*tmyaaB + 2*tmyaBB)^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*(tmyaaB + tmyaab + 2*tmyaBb)^2 + allfreq[2]^2*allfreq[4]^2*(2*tmyaab + 2*tmyabb)^2

#Dominance-dominance variance, VAD
tlVDD<-allfreq[1]^2*allfreq[3]^2*tmyAABB^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*tmyAABb^2 +
	   allfreq[1]^2*allfreq[4]^2*tmyAAbb^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*tmyAaBB^2 +
		4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*tmyAaBb^2 +
	   2*allfreq[1]*allfreq[2]*allfreq[4]^2*tmyAabb^2 + allfreq[2]^2*allfreq[3]^2*tmyaaBB^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*tmyaaBb^2 + allfreq[2]^2*allfreq[4]^2*tmyaabb^2

#Total genetic variance
tlgenvartot<-tlVA + tlVD + tlVAA + tlVAD + tlVDD
tlepi<-tlVAA + tlVAD + tlVDD
tlgenvar<-c(tlgenvartot,tlVA,tlVD,tlVAA,tlVAD,tlVDD,tlepi)
tlgenher<-c(tlgenvartot/vartrait,tlVA/vartrait,tlVD/vartrait,tlVAA/vartrait,tlVAD/vartrait,tlVDD/vartrait,tlepi/vartrait)

#Pak Sham SumSquare(SS) decomposition. Should be superflous when flaw has been defined.

SS1<- allfreq[1]^2*allfreq[3]^2*mAABB^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*mAABb^2 +
	  allfreq[1]^2*allfreq[4]^2*mAAbb^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*mAaBB^2 +
	  4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*mAaBb^2 + 
	   2*allfreq[1]*allfreq[2]*allfreq[4]^2*mAabb^2 + allfreq[2]^2*allfreq[3]^2*maaBB^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*maaBb^2 + allfreq[2]^2*allfreq[4]^2*maabb^2

SS2<- allfreq[1]^2*allfreq[3]^2*(mAAyy+mxxBB)^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*(mAAyy+mxxBb)^2 +
	  allfreq[1]^2*allfreq[4]^2*(mAAyy+mxxbb)^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*(mAayy+mxxBB)^2 +
	  4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*(mAayy+mxxBb)^2 + 
	  2*allfreq[1]*allfreq[2]*allfreq[4]^2*(mAayy+mxxbb)^2 + allfreq[2]^2*allfreq[3]^2*(maayy+mxxBB)^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*(maayy+mxxBb)^2 + allfreq[2]^2*allfreq[4]^2*(maayy+mxxbb)^2

SS3<- allfreq[1]^2*allfreq[3]^2*(2*tmyA + 2*tmyB)^2 + 2*allfreq[1]^2*allfreq[3]*allfreq[4]*(2*tmyA + tmyB + tmyb)^2 +
	  allfreq[1]^2*allfreq[4]^2*(2*tmyA + 2*tmyb)^2 + 2*allfreq[1]*allfreq[2]*allfreq[3]^2*(tmyA + tmya + 2*tmyB)^2 +
	  4*allfreq[1]*allfreq[2]*allfreq[3]*allfreq[4]*(tmyA + tmya + tmyB + tmyb)^2 + 
	  2*allfreq[1]*allfreq[2]*allfreq[4]^2*(tmyA + tmya + 2*tmyb)^2 +	 allfreq[2]^2*allfreq[3]^2*(2*tmya + 2*tmyB)^2 +
	   2*allfreq[2]^2*allfreq[3]*allfreq[4]*(2*tmya + tmyB + tmyb)^2 + allfreq[2]^2*allfreq[4]^2*(2*tmya + 2*tmyb)^2

SSVA<-SS3
SSVD<-SS2-SS3
SSVI<-SS1-SS2

SSgenher<-c(SS1/vartrait,SSVA/vartrait,SSVD/vartrait,SSVI/vartrait)

#Now based on counting
#Use counts instaed of allelfrequences: HWE and LD should be unnecessary.
#trlength<-c(    ltr1,   ltr2,   ltr3,   ltr4,   ltr5,   ltr6,   ltr7,   ltr8,   ltr9)
#trcontent<-list(gdfAABB,gdfAABb,gdfAAbb,gdfAaBB,gdfAaBb,gdfAabb,gdfaaBB,gdfaaBb,gdfaabb)	

#frequncies of genotypew
ntrlength<-trlength/sum(trlength)

#Additive genic variance, VA
ctlVA<-ntrlength[1]*(2*tmyA + 2*tmyB)^2 + ntrlength[2]*(2*tmyA + tmyB + tmyb)^2 +
	   ntrlength[3]*(2*tmyA + 2*tmyb)^2 + ntrlength[4]*(tmyA + tmya + 2*tmyB)^2 +
		ntrlength[5]*(tmyA + tmya + tmyB + tmyb)^2 +
	   ntrlength[6]*(tmyA + tmya + 2*tmyb)^2 + ntrlength[7]*(2*tmya + 2*tmyB)^2 +
	   ntrlength[8]*(2*tmya + tmyB + tmyb)^2 + ntrlength[9]*(2*tmya + 2*tmyb)^2

#Dominance variance, VD
ctlVD<-ntrlength[1]*(tmyAA + tmyBB)^2 + ntrlength[2]*(tmyAA + tmyBb)^2 +
	   ntrlength[3]*(tmyAA + tmybb)^2 + ntrlength[4]*(tmyAa + tmyBB)^2 +
		ntrlength[5]*(tmyAa + tmyBb)^2 +
	   ntrlength[6]*(tmyAa + tmybb)^2 + ntrlength[7]*(tmyaa + tmyBB)^2 +
	   ntrlength[8]*(tmyaa + tmyBb)^2 + ntrlength[9]*(tmyaa + tmybb)^2

#Additive-Additive variance, VAA
ctlVAA<-ntrlength[1]*(4*tmyAB)^2 + ntrlength[2]*(2*tmyAB + 2*tmyAb)^2 +
	   ntrlength[3]*(4*tmyAb)^2 + ntrlength[4]*(2*tmyAB + 2*tmyaB)^2 +
		ntrlength[5]*(tmyAB + tmyAb + tmyaB + tmyab)^2 +
	   ntrlength[6]*(2*tmyAb + 2*tmyab)^2 + ntrlength[7]*(4*tmyaB)^2 +
	   ntrlength[8]*(2*tmyaB + 2*tmyab)^2 + ntrlength[9]*(4*tmyab)^2

#Additive-dominance variance, VAD
ctlVAD<-ntrlength[1]*(2*tmyAAB + 2*tmyABB)^2 + ntrlength[2]*(2*tmyABb + tmyAAB + tmyAAb)^2 +
	   ntrlength[3]*(2*tmyAAb + 2*tmyAbb)^2 + ntrlength[4]*(2*tmyAaB + tmyABB + tmyaBB)^2 +
		ntrlength[5]*(tmyAaB + tmyAab + tmyABb + tmyaBb)^2 +
	   ntrlength[6]*(2*tmyAab + tmyAbb + tmyabb)^2 + ntrlength[7]*(2*tmyaaB + 2*tmyaBB)^2 +
	   ntrlength[8]*(tmyaaB + tmyaab + 2*tmyaBb)^2 + ntrlength[9]*(2*tmyaab + 2*tmyabb)^2

#Dominance-dominance variance, VAD
ctlVDD<-ntrlength[1]*tmyAABB^2 + ntrlength[2]*tmyAABb^2 +
	   ntrlength[3]*tmyAAbb^2 + ntrlength[4]*tmyAaBB^2 +
	   ntrlength[5]*tmyAaBb^2 +
	   ntrlength[6]*tmyAabb^2 + ntrlength[7]*tmyaaBB^2 +
	   ntrlength[8]*tmyaaBb^2 + ntrlength[9]*tmyaabb^2

#Total genetic variance
ctlgenvartot<-ctlVA + ctlVD + ctlVAA + ctlVAD + ctlVDD
ctlepi<-ctlVAA + ctlVAD + ctlVDD
ctlgenvar<-c(ctlgenvartot,ctlVA,ctlVD,ctlVAA,ctlVAD,ctlVDD,ctlepi)
#ctlgenher<-c(ctlgenvartot/vartrait,ctlVA/vartrait,ctlVD/vartrait,ctlVAA/vartrait,ctlVAD/vartrait,ctlVDD/vartrait,ctlepi/vartrait)
ctlgenher<-ctlgenvar/vartrait

#SS with counts
cSS1<- ntrlength[1]*mAABB^2 + ntrlength[2]*mAABb^2 + ntrlength[3]*mAAbb^2 + ntrlength[4]*mAaBB^2 + ntrlength[5]*mAaBb^2 + 
	   ntrlength[6]*mAabb^2 + ntrlength[7]*maaBB^2 + ntrlength[8]*maaBb^2 + ntrlength[9]*maabb^2

cSS2<- ntrlength[1]*(mAAyy+mxxBB)^2 + ntrlength[2]*(mAAyy+mxxBb)^2 + ntrlength[3]*(mAAyy+mxxbb)^2 + ntrlength[4]*(mAayy+mxxBB)^2 +
	    ntrlength[5]*(mAayy+mxxBb)^2 + ntrlength[6]^2*(mAayy+mxxbb)^2 + ntrlength[7]*(maayy+mxxBB)^2 +
	    ntrlength[8]*(maayy+mxxBb)^2 + ntrlength[9]*(maayy+mxxbb)^2

cSS3<- ntrlength[1]*(2*tmyA + 2*tmyB)^2 + ntrlength[2]*(2*tmyA + tmyB + tmyb)^2 +
	  ntrlength[3]*(2*tmyA + 2*tmyb)^2 + ntrlength[4]*(tmyA + tmya + 2*tmyB)^2 +
	  ntrlength[5]*(tmyA + tmya + tmyB + tmyb)^2 + 
	  ntrlength[6]*(tmyA + tmya + 2*tmyb)^2 +	ntrlength[7]*(2*tmya + 2*tmyB)^2 +
	   ntrlength[8]*(2*tmya + tmyB + tmyb)^2 + ntrlength[9]*(2*tmya + 2*tmyb)^2

cSSVA<-cSS3
cSSVD<-cSS2-cSS3
cSSVI<-cSS1-cSS2

cSSgenher<-c(cSS1/vartrait,cSSVA/vartrait,cSSVD/vartrait,cSSVI/vartrait)


#NB alt dette forudsætter HWE og LE. Kan man alternativt bruge counts? Prøv!!
#sham one locus
#Single locus headings
	slADGhead1<-c("Pak Sham variance decomposition")
	slADGhead2<-c("Single locus effects and residual dominance deviations")
	slADGhead3<-c(gname1,"","","","",gname2)
	slADGhead4<-c("Add A","Add a","Dom AA","Dom Aa","Dom aa","Add B","Add b","Dom BB","Dom Bb","Dom bb")
	slADGhead5<-c("Total Variance","Additive A","Dominant A","Genotypic A","Additive B","Dominant B","Genotypic B")
	slADGhead6<-c("Heritabilities:","",herADG)
	writeToFile("", paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",slADGhead1), nrow=1), paste(eSave, epiext,sep=""))

	writeToFile("", paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",slADGhead2), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",slADGhead3), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",slADGhead4), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",sgeneffect), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",slADGhead5), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Variance:",varADG), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",slADGhead6), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))

#sham two locus


	writeToFile(matrix(c("","","Two-locus model"), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))	
	tgeneffhead<-matrix(c("","","Additive:","Gene A","Gene a","GeneB","Gene b"),nrow=1)

writeToFile(matrix(c("",tgeneffhead),nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",tgeneff), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile("", paste(eSave, epiext,sep=""))
	tdomeffhead<-c("","Dominance:","AA","Aa","aa","BB","Bb","bb")
	writeToFile(matrix(c("","",tdomeffhead), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",tdomeff), nrow=1), paste(eSave, epiext,sep=""))

writeToFile("", paste(eSave, epiext,sep=""))
	tAAeffhead<-c("Add-Add:","AB","Ab","aB","ab")
	writeToFile(matrix(c("","",tAAeffhead), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",tAAeff), nrow=1), paste(eSave, epiext,sep=""))

tADeffhead<-c("Add-Dom:","AAB","AAb","AaB","Aab","aaB","aab","ABB","aBB","ABb","aBb","Abb","abb")
# Redit : write.table("", paste(eSave, epiext,sep="",sep=""), sep = "\t", append = T,quote=F, col.names=F,row.names=F)
writeToFile("", paste(eSave, epiext,sep="")) # multiple "sep" arguments not accepted by R 

#print("hej")
writeToFile(matrix(c("","",tADeffhead), nrow=1), paste(eSave, epiext,sep=""))

writeToFile(matrix(c("","",tADeff), nrow=1), paste(eSave, epiext,sep=""))
	tDDeffhead<-c("Dom-Dom:","","AABB","AABb","AAbb","AaBB","AaBb","Aabb","aaBB","aaBb","aabb")

writeToFile("", paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",tDDeffhead), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",tDDeff), nrow=1), paste(eSave, epiext,sep=""))
	tlgenvarhead1<-c("Genetic variance")
	tlgenvarhead2<-c("Total genetic variance","Additive","Dominance","Add-Add","Add-Dom","Dom-Dom","Epi")
	tlgenvarhead3<-c("Total genetic variance SS","Additive","Dominance","Epi")
	writeToFile("", paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","",tlgenvarhead1), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",tlgenvarhead2), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","",tlgenvar), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","Heritability:",tlgenher), nrow=1), paste(eSave, epiext,sep=""))

	writeToFile(matrix(c("","","",tlgenvarhead3), nrow=1), paste(eSave, epiext,sep=""))
	writeToFile(matrix(c("","","SSvariance:",SSgenher), nrow=1), paste(eSave, epiext,sep=""))
	
	writeToFile("", paste(eSave, epiext,sep=""))

#Output or signifcant values only

#if(signval[9]=="T"){(signval[1]<epistsign || signval[2]<epistsign)
#	{
	#???????????????????
#	write.table(matrix(c("","","","","PS Heritability","","",tlgenvarhead2), nrow=1), paste(esSave, epiexts,sep=""), sep = "\t", append = T)
#	write.table(matrix(c("","","","","","","",tlgenher), nrow=1), paste(esSave, epiexts,sep=""), sep = "\t", append = T)
#	write.table("", paste(esSave, epiexts,sep=""), sep = "\t", append = T)
#}#end of signíficant output
GenVar<-c(tlgenher,ctlgenher, SSgenher,cSSgenher)
return(GenVar)
}
