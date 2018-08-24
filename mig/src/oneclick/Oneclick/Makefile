# Makefile - build helper
# Copyright (C) 2007  Martin Rehr
# 
# This file is part of MiG.
# 
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

JAVAC=javac
JFLAGS=-source 1.4 -target 1.4 -classpath .
SCP=scp

JAR=zip
JAR_DEST=amigos18.diku.dk:~/mig/java-bin
JARSIGNER=jarsigner

JAVADOC=javadoc
JAVADOC_DIR=./javadoc
JAVADOC_DEST=lucia.imada.sdu.dk:~/WWWpublic/oneclick
JAVADOC_SRC_FILES=../MiG/oneclick/File.java\
	          ../MiG/oneclick/Job.java\
	          ../MiG/oneclick/Exception.java\
	          ../MiG/oneclick/FileException.java


SOURCES=$(shell find . -name '*.java' -print)
CLASSES=${SOURCES:.java=.class}

all: MiGOneClickCodebase.jar MiGOneClickConsole.jar doc

#all: MiGOneClickCodebase.jar doc

# The documentation
doc:	 
	 cd $(JAVADOC_DIR) && $(JAVADOC) $(JAVADOC_SRC_FILES)


classes: $(CLASSES)

# The codebase for the MiG-server.
MiGOneClickCodebase.jar: $(CLASSES)
	 $(JAR) -r $@ `find ./MiG/oneclick -name '*.class'`
	 #$(JARSIGNER) $@ $@

# The console application.
MiGOneClickConsole.jar: $(CLASSES)
	 $(JAR) $@ MiGOneClickConsole.class MiG/oneclick/HttpsConnection*.class

%.class: %.java
	 $(JAVAC) $(JFLAGS) $<


clean:	 
	 find . -name '*.jar' -print | xargs $(RM)
	 find . -name '*.class' -print | xargs $(RM)
	 find . -name '*~' -print | xargs $(RM)
	 rm -rf javadoc/*
