######################################################################
#
# GNUmakefile for the docker floodlight stuffs
#
######################################################################

DOCKER_USER			= $(USER)
DOCKER_HOME			= $(HOME)
DOCKER_UID			= $(shell id -u)
DOCKER_GID			= $(shell id -g)
DOCKER_TMPDIR			= $(DOCKER_HOME)/tmp/switchlight-docker

DOCKER_IMAGE			= $(DOCKER_USER)/switchlight
DOCKER_HOST_CONTAINER		= $(DOCKER_USER)_switchlight_host
DOCKER_CONTAINER		= $(DOCKER_USER)_switchlight

DOCKER_HOST_VOLUMES		= \
  -v /home/roth:/home/roth \
  -v /opt/bsn/container:/opt/bsn/container:ro \
  -v /dev/log:/dev/log \
  -v /lib/modules:/lib/modules:ro \
  # THIS LINE INTENTIONALLY LEFT BLANK

DOCKER_OS			= switch_team_deb7_builder

-include docker.mk

default: Dockerfile apt.conf sudoers acng.conf

include ../../../make/rules.mk

