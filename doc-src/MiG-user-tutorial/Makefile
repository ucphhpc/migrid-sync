# Make a number of formats from the txt2tags formatted t2t file
#


%.txt:	%.t2t
	txt2tags -t txt -o $@ $<

%.html:	%.t2t
	txt2tags -t html -o $@ $<

%.tex:	%.t2t
	txt2tags -t tex -o $@ $<

%.dvi:	%.tex
	latex $<

%.ps:	%.dvi
	dvips -o $@ $<

%.pdf:	%.tex
	pdflatex $<

clean:	
	rm -f *~ *.log *.aux *.dvi *.ps *.pdf *.tex  *.txt *.html
