PREFIX = /usr/local

help:
	@echo "Available targets:"
	@echo
	@echo "clean"
	@echo "install [PREFIX=prefix]"

clean:
	$(MAKE) -C src/web clean
	rm -rf build
	find . \( -name '*~' -o -name '*.pyc' \) -exec rm -f {} \;

install:
	python setup.py install --prefix=$(PREFIX)

check:
	python src/test/alltests.py
