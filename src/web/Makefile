CLASSES = Page Root
CLASSFILES = $(CLASSES:=.cpy)

all: webkofoto.py

run: all
	python webkofoto.py

webkofoto.py: $(CLASSFILES)
	cherrypy -O $@ $^

clean:
	rm -f webkofoto.py *~
