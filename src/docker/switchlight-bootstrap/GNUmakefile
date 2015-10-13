######################################################################
#
# GNUmakefile for the docker floodlight stuffs
#
######################################################################

DOCKER_PROFILE			= switchlight
DOCKER_OS			= opennetworklinux/onl-build:1.5

include ../../../make/config.mk

-include docker.mk

default: Dockerfile apt.conf sudoers acng.conf

include ../../../make/rules.mk

