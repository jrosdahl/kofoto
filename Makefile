PREFIX = /usr/local

VERSION = $(shell sed -n 's/^version = "\(.*\)"$$/\1/p' src/lib/kofoto/version.py)

help:
	@echo "Available targets:"
	@echo
	@echo "check"
	@echo "clean"
	@echo "dist"
	@echo "install [PREFIX=prefix]"

clean:
	$(MAKE) -C src/web clean
	rm -rf build dist
	find . \( -name '*~' -o -name '.*~' -o -name '.#*' -o -name '*.pyc' \
		  -o -name '*.orig' -o -name '*.bak' -o -name '*.rej' \
		  -o -name MANIFEST \
	       \) -exec rm -f {} \;

install:
	./setup.py install --prefix=$(PREFIX)

ifeq "$(shell echo $(VERSION) | grep pre)" ""
dist: clean dist_all
else
dist: clean dist_pre
endif

dist_all: dist_pre dist_rpm dist_debian
dist_pre: dist_source dist_binary_targz dist_windows_installer

dist_source:
	./setup.py sdist --formats=gztar,zip

dist_binary_targz:
	./setup.py bdist --formats=gztar

dist_windows_installer:
	./setup.py windows bdist_wininst --install-script gkofoto-windows-postinstall.py

dist_rpm:
	./setup.py bdist --formats=rpm

dist_debian:
	mkdir dist/debiantmp
	cp dist/kofoto-$(VERSION).tar.gz dist/debiantmp/kofoto_$(VERSION).orig.tar.gz
	cd dist/debiantmp && tar xzf kofoto_$(VERSION).orig.tar.gz
	cp -r packaging/debian dist/debiantmp/kofoto-$(VERSION)
	rm -rf dist/debiantmp/kofoto-$(VERSION)/debian/.svn
	cd dist/debiantmp/kofoto-$(VERSION) && debuild
	mkdir -p dist/debian
	mv dist/debiantmp/kofoto_$(VERSION)-*.deb dist/debian
	mv dist/debiantmp/kofoto_$(VERSION).orig.tar.gz dist/debian
	mv dist/debiantmp/kofoto_$(VERSION)-*.diff.gz dist/debian
	mv dist/debiantmp/kofoto_$(VERSION)-*.dsc dist/debian
	cd dist/debian && dpkg-scanpackages . /dev/null 2>/dev/null | gzip -9c >Packages.gz
	cd dist/debian && dpkg-scansources . /dev/null 2>/dev/null | gzip -9c >Sources.gz
	rm -rf dist/debiantmp

check:
	python src/test/alltests.py

.PHONY: help clean install dist check
