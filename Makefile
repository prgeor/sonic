INTERACTIVE := $(shell [ -t 0 ] && echo 1)

# tools
PYTHON2 ?= python2
PYTHON3 ?= python3
MKDIR ?= mkdir
CP ?= cp

# envs
KVERSION       ?= $(shell uname -r)
KERNEL_SRC     ?= /lib/modules/$(KVERSION)/build
KERNEL_DST     := /lib/modules/$(KVERSION)
BASE_DIR       ?= $(CURDIR)
MODULE_SRC     := $(BASE_DIR)/src
TEST_DIR       := $(BASE_DIR)/tests
BUILD_DIR      := $(BASE_DIR)/build

# sources
BIN_SRC        := $(wildcard $(BASE_DIR)/utils/*)
RULE_SRC       := $(wildcard $(BASE_DIR)/udev/*)
SERVICE_SRC    := $(wildcard $(BASE_DIR)/systemd/*)

# packaging
PACKAGE_NAME     ?= arista
PACKAGE_VERSION  ?= $(shell git rev-parse --short HEAD)
PACKAGE_DATE     ?= $(shell git log -1 --format='%ad' --date=short)
PY2_PACKAGE_NAME ?= $(PACKAGE_NAME)
PY3_PACKAGE_NAME ?= $(PACKAGE_NAME)

DESTDIR         ?= $(CURDIR)/install
BIN_DESTDIR     ?= $(DESTDIR)/usr/bin
DRV_DESTDIR     ?= $(DESTDIR)/$(KERNEL_DST)/$(INSTALL_MOD_DIR)
PY2_DESTDIR     ?= $(DESTDIR)
PY3_DESTDIR     ?= $(DESTDIR)
RULE_DESTDIR    ?= $(DESTDIR)/etc/udev/rules.d
SYSTEMD_DESTDIR ?= $(DESTDIR)/lib/systemd/system
LIB_DESTDIR     ?= $(DESTDIR)/usr/lib

# build
PY_BUILD_ARGS ?=
PY2_BUILD_ARGS ?= $(PY_BUILD_ARGS) --build-base=$(BUILD_DIR)/python2
PY3_BUILD_ARGS ?= $(PY_BUILD_ARGS) --build-base=$(BUILD_DIR)/python3
PYLINTRC ?= $(BASE_DIR)/.pylintrc
PYLINT_BLACKLIST ?= $(shell "cat $(BASE_DIR)/.pylint_blacklist | tr '\n' ','")
PYLINT_JOBS ?= 4
PYTEST_ARGS ?=
PY_TARGETS ?= py3

# scd
ARISTA_SCD_DRIVER_CONFIG ?= m
export ARISTA_SCD_DRIVER_CONFIG
EXTRA_SYMBOLS := /lib/modules/$(KVERSION)/extra/scd-Module.symvers
export EXTRA_SYMBOLS

# dev
PY2_VENV_PATH ?= venv2
PY3_VENV_PATH ?= venv3

define library_version
# autogenerated by the build system
__VERSION__ = "$(PACKAGE_VERSION)"
__DATE__ = "$(PACKAGE_DATE)"
endef
export library_version

ifndef INTERACTIVE
PYTEST_ARGS ?= '-v'
endif

all:
	@echo "Nothing to do."
#
# build targets
#

build-drivers:
	EXTRA_SYMBOLS=$(EXTRA_SYMBOLS) $(MAKE) -C $(KERNEL_SRC) M=$(MODULE_SRC)

build-libs:
	$(MAKE) -C lib

build-py2:
	echo "$$library_version" > $(BASE_DIR)/$(PACKAGE_NAME)/__version__.py
	$(PYTHON2) setup.py build $(PY2_BUILD_ARGS)

build-py3:
	echo "$$library_version" > $(BASE_DIR)/$(PACKAGE_NAME)/__version__.py
	$(PYTHON3) setup.py build $(PY3_BUILD_ARGS)

build-py: $(addprefix build-,$(PY_TARGETS))

build: build-drivers build-py build-libs

#
# clean targets
#

clean-drivers:
	$(RM) $(MODULE_SRC)/*.o $(MODULE_SRC)/*.ko $(MODULE_SRC)/*.mod.c $(MODULE_SRC)/.*.cmd
	$(RM) $(MODULE_SRC)/Module.markers $(MODULE_SRC)/Module.symvers $(MODULE_SRC)/modules.order
	$(RM) -r $(MODULE_SRC)/.tmp_versions

clean-py2:
	$(PYTHON2) setup.py clean $(PY2_BUILD_ARGS)
	find "$(BASE_DIR)/arista" -name '*.pyc' -delete

clean-py3:
	$(PYTHON3) setup.py clean $(PY3_BUILD_ARGS)
	find "$(BASE_DIR)/arista" -name '__pycache__' -exec rm -rf {} +

clean-py: $(addprefix clean-,$(PY_TARGETS))

clean-libs:
	$(MAKE) -C lib clean

clean: clean-py clean-drivers clean-libs

distclean: clean
	$(RM) -r "$(BASE_DIR)/*.egg-info" "$(BASE_DIR)/build" "$(BASE_DIR)/install"

#
# install targets
#

install-py2:
	$(MKDIR) -p $(PY2_DESTDIR)
	$(PYTHON2) setup.py install --root=$(PY2_DESTDIR) $(PY_INSTALL_ARGS)

install-py3:
	$(MKDIR) -p $(PY3_DESTDIR)
	$(PYTHON3) setup.py install --root=$(PY3_DESTDIR) $(PY_INSTALL_ARGS)

install-drivers:
	$(MKDIR) -p $(DRV_DESTDIR)
	$(CP) $(MODULE_SRC)/*.ko $(DRV_DESTDIR)

install-bin:
	$(MKDIR) -p $(BIN_DESTDIR)
	$(CP) $(BIN_SRC) $(BIN_DESTDIR)

install-systemd:
	$(MKDIR) -p $(SYSTEMD_DESTDIR)
	$(CP) $(SERVICE_SRC) $(SYSTEMD_DESTDIR)

install-udev:
	$(MKDIR) -p $(RULE_DESTDIR)
	$(CP) $(RULE_SRC) $(RULE_DESTDIR)

install-libs:
	$(MAKE) -C lib install DESTDIR=$(LIB_DESTDIR)

install-fs: install-bin install-systemd install-udev

install-py: $(addprefix install-,$(PY_TARGETS))

install: install-py install-drivers install-libs install-fs

#
# test targets
#

test-py2:
	$(PYTHON2) -m pytest $(PYTEST_ARGS)

test-py3:
	$(PYTHON3) -m pytest $(PYTEST_ARGS)

test-py: $(addprefix test-,$(PY_TARGETS))

pylint:
	# NOTE: for now we only check py2/py3 compatibility.
	#       once these are solved we should enable the more generic pylint.
	# FIXME: make this fatal as soon as possible
	-pylint --py3k \
	   --jobs=$(PYLINT_JOBS) \
	   --rcfile=$(PYLINTRC) \
	   --ignore=$(PYLINT_BLACKLIST) \
	   $(PACKAGE_NAME)

pycoverage:
	$(PYTHON3) -m pytest --cov-config=.coveragerc --cov-report term-missing:skip-covered --cov $(PACKAGE_NAME)

test: test-py pylint

#
# dev tools
#

$(PY2_VENV_PATH):
	virtualenv $@
	@echo "source $@/bin/activate"
	@echo "python setup.py develop"

$(PY3_VENV_PATH):
	$(PYTHON3) -m venv $@
	@echo "source $@/bin/activate"
	@echo "python setup.py develop"

print-%:
	@echo $($*)

