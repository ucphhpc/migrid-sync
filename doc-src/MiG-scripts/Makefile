# Make multiple doc formats from txt2tags source
#

docfiles = MiG-user-scripts.html MiG-user-scripts.pdf

.PHONY: all

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

docs: $(docfiles)

all: docs clean

clean:	
	rm -f *~ *.log *.aux *.dvi *.ps *.pdf *.tex *.txt
