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

bootstrap: bootstrap-switchlight

BOOTSTRAP_PACKAGES		= \
  python-dnspython \
  python-pyroute2 \
  # THIS LINE INTENTIONALLY LEFT BLANK

bootstrap-switchlight:
	docker exec $(DOCKER_CONTAINER_ID) sudo DEBIAN_FRONTEND=noninteractive apt-get -y install $(BOOTSTRAP_PACKAGES)
