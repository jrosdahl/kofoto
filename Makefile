PREFIX = /usr/local

help:
	@echo "Available targets:"
	@echo
	@echo "clean"
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

dist:
	./setup.py sdist --formats=gztar,zip
	./setup.py bdist --formats=gztar,rpm
	./setup.py windows bdist_wininst --install-script gkofoto-windows-postinstall.py

check:
	python src/test/alltests.py

.PHONY: help clean install dist check
