######################################################################
#
# GNUmakefile for the docker floodlight stuffs
#
######################################################################

DOCKER_USER			= $(USER)
DOCKER_HOME			= $(HOME)
DOCKER_UID			= $(shell id -u)
DOCKER_GID			= $(shell id -g)
DOCKER_TMPDIR			= $(DOCKER_HOME)/tmp/floodlight-docker

DOCKER_IMAGE			= $(DOCKER_USER)/floodlight
DOCKER_CONTAINER		= $(DOCKER_USER)_floodlight
DOCKER_HOST_CONTAINER		= $(DOCKER_CONTAINER)_host

DOCKER_HOST_VOLUMES		= \
  -v /home/roth:/home/roth \
  -v /opt/bsn/container:/opt/bsn/container:ro \
  -v /dev/log:/dev/log \
  -v /lib/modules:/lib/modules:ro \
  # THIS LINE INTENTIONALLY LEFT BLANK

DOCKER_OS			= ubuntu:14.04

-include docker.mk

default: Dockerfile apt.conf

include ../../../make/rules.mk

# See https://bigswitch.atlassian.net/wiki/display/BSC/Development+Environment+Setup
BOOTSTRAP_PACKAGES		= \
  ssh git maven openjdk-7-jdk python-setuptools zip \
  build-essential cowbuilder python-vm-builder \
  reprepro parted gddrescue e2fsprogs mount extlinux coreutils zip debhelper zerofree \
  apt-cacher-ng \
  ccache \
  # THIS LINE INTENTIONALLY LEFT BLANK

bootstrap: bootstrap-floodlight

bootstrap-floodlight:
	docker exec $(DOCKER_CONTAINER_ID) sudo DEBIAN_FRONTEND=noninteractive apt-get -y install $(BOOTSTRAP_PACKAGES)
