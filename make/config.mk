######################################################################
#
# config.mk
#
######################################################################

DOCKER_USER			= $(USER)
DOCKER_HOME			= $(HOME)
DOCKER_UID			= $(shell id -u)
DOCKER_GID			= $(shell id -g)

ifeq ($(shell uname -s),Darwin)
DOCKER_TMPDIR			= $(DOCKER_HOME)/Library/Caches/docker/$(DOCKER_PROFILE)
else
ifeq ($(shell uname -s),Linux)
ifdef XDG_CACHE_HOME
DOCKER_TMPDIR			= $(XDG_CACHE_HOME)/docker/$(DOCKER_PROFILE)
else
DOCKER_TMPDIR			= $(DOCKER_HOME)/.cache/docker/$(DOCKER_PROFILE)
endif
else
DOCKER_TMPDIR			= $(DOCKER_HOME)/tmp
endif
endif

DOCKER_IMAGE			= $(DOCKER_USER)/$(DOCKER_PROFILE)
DOCKER_CONTAINER		= $(DOCKER_USER)_$(DOCKER_PROFILE)
DOCKER_HOST_CONTAINER		= $(DOCKER_CONTAINER)_host

DOCKER_HOST_VOLUMES		= \
  -v /dev/log:/dev/log \
  -v /lib/modules:/lib/modules:ro \
  # THIS LINE INTENTIONALLY LEFT BLANK

ifeq ($(shell uname -s),Darwin)
DOCKER_HOST_VOLUMES		+= \
  -v /Users:/Users \
  -v /Volumes/data:/Volumes/data \
  -v /Volumes/spool:/Volumes/spool \
  # THIS LINE INTENTIONALLY LEFT BLANK
else
ifeq ($(shell uname -s),Linux)
DOCKER_HOST_VOLUMES		+= \
  -v $(DOCKER_HOME):$(DOCKER_HOME) \
  -v /opt/bsn/container:/opt/bsn/container:ro \
  # THIS LINE INTENTIONALLY LEFT BLANK
endif
endif
