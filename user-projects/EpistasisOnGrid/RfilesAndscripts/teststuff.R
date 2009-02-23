

testfunct <- function(arg){
forvar
}


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
args <- commandArgs(TRUE)

print("arguments ")
print(args)

testvec <-  c(1,2,5,6,7,9)
testvec2 <-  c(T,F,T,F,T,T)
testvec3 <- c(2,4)
testna <- c(NA, NA, NA, NaN, NaN, Inf, Inf)
#testna <- as.character(testna)

typeof(testna[[7]])
class(testna[[7]])
testna[[7]] == Inf

for(i in 1:length(testna)){
  forvar <- 7
  testfunct(4)
  if(is.na(testna[[i]])){

#     if(is.inf(testna[[i]])){
    
    print("found NA")
  }
}

#aov(traitVector~geneVector1+geneVector2 + geneVector1*geneVector2, data=traittrim1, na.action=na.exclude)

#nedarvet <- c(1,2,3,4,5)
test1var <- "test1var"
#nedarvtest()

forvar+1

testvec + testvec2

data1 <- data.frame(testvec, testvec2)
data12 <- data.frame(testvec, testvec3)
#mat <- matrix(1,length(testvec), length(testvec2))
hej <- testvec
data2 <- aov(hej ~ testvec + testvec2, data=data12, na.action=na.exclude)

#data ~ testvec + testvec2 + testvec*testvec2
data2
summa <- summary.aov(data2)
sum1 <- summa[[1]]
class(summa[[1]][[1]])
names(sum1)
sum1["Mean Sq"]
names(summa)
print(model.tables(data2,"means"),digits=3)  




#extract(summa)

testvec3 <- c(11,2,453,"sdfasdkjh", 4,5,'?    ','?    ','?    ',4,5,6)

#as.numeric(testvec3)
strtrim(testvec3,2)

testvec3 <- gsub(" ", "",testvec3)

vec <- c(0)

var(vec,na.rm=T,use=)
stop("hold it")
#misv <- "?"
#factor(as.character(testvec3))
#factor(as.character(testvec3), exclude=misv)


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


trimmer <- function(arg){
gsub(arg)
}

testfunct <- function(arg){
forvar
}
