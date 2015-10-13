######################################################################
#
# GNUmakefile for the docker floodlight stuffs
#
######################################################################

DOCKER_PROFILE			= switchlight
##DOCKER_OS			= switch_team_deb7_builder
DOCKER_OS			= bigswitchnetworks/onl_deb7_builder

include ../../../make/config.mk

-include docker.mk

default: Dockerfile apt.conf sudoers acng.conf

include ../../../make/rules.mk

