######################################################################
#
# GNUmakefile for the docker floodlight stuffs
#
######################################################################

DOCKER_PROFILE			= floodlight
DOCKER_OS			= ubuntu:14.04

include ../../../make/config.mk

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
	docker exec $(DOCKER_CONTAINER_ID) sudo apt-get update
	docker exec $(DOCKER_CONTAINER_ID) sudo DEBIAN_FRONTEND=noninteractive apt-get -y install $(BOOTSTRAP_PACKAGES)
