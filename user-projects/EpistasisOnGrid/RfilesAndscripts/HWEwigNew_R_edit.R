"HWEwigNew" = function(tall,g1,g2,g3)
{
	if(g1 < 0 || g2 < 0 || g3 < 0)
		return(-1.)
	# total number of genotypes   
	N <- tall
	# rare homozygotes, common homozygotes
	homr <- min(g1, g3)
	homc <- max(g1, g3)
	# number of rare allele copies
	rare <- homr * 2 + g2
	# Initialize probability array
	probs <- rep(0, 1 + rare)
	# Find midpoint of the distribution
	mid <- floor((rare * (2 * N - rare))/(2 * N))
	if((mid %% 2) != (rare %% 2)){mid <- mid + 1}
	probs[mid + 1] <- 1.
	mysum <- 1.
	# Calculate probablities from midpoint down 
	curr.hets <- mid
	curr.homr <- (rare - mid)/2
	curr.homc <- N - curr.hets - curr.homr
	while(curr.hets >= 2) {
		probs[curr.hets - 1] <- (probs[curr.hets + 1] * curr.hets * (curr.hets - 1.))/(4. * (curr.homr + 1.) * (curr.homc + 1.))
		mysum <- mysum + probs[curr.hets - 1]
		# 2 fewer heterozygotes -> add 1 rare homozygote, 1 common homozygote
		curr.hets <- curr.hets - 2
		curr.homr <- curr.homr + 1
		curr.homc <- curr.homc + 1
	}
	# Calculate probabilities from midpoint up
	curr.hets <- mid
	curr.homr <- (rare - mid)/2
	curr.homc <- N - curr.hets - curr.homr
	while(curr.hets <= rare - 2) {
		probs[curr.hets + 3] <- (probs[curr.hets + 1] * 4. * curr.homr * curr.homc)/((curr.hets + 2.) * (curr.hets + 1.))
		mysum <- mysum + probs[curr.hets + 3]
		# add 2 heterozygotes -> subtract 1 rare homozygtote, 1 common homozygote
		curr.hets <- curr.hets + 2
		curr.homr <- curr.homr - 1
		curr.homc <- curr.homc - 1
	}
	# P-value calculation
	target <- probs[g2 + 1]
	pme <- min(1., sum(probs[probs <= target])/mysum)
	#NB Apparently the summary terms in probs has to be en brackets at least for the first term (e.g.g2+1)
	#This works in phi, but are implemented all over in both plo and phi to be sure
	plo <- min(1., sum(probs[1:(g2 + 1)])/mysum)
	phi <- min(1., sum(probs[(g2 + 1):(rare + 1)])/mysum)
	parsewig <- c(pme, plo, phi)
	return(parsewig)
}
