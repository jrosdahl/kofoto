CLASSES = Page Root
CLASSFILES = $(CLASSES:=.cpy)

all: kofotoweb/server.py

run: all
	python webkofoto

kofotoweb:
	mkdir -p $@
	touch $@/__init__.py

kofotoweb/server.py: kofotoweb $(CLASSFILES)
	cherrypy -O $@ $(CLASSFILES)

clean:
	rm -rf *~ *.py[co] kofotoweb
