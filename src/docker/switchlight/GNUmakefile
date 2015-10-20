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

Dockerfile: apt.conf sudoers acng.conf switch-nfs.list

switch-nfs.list:
	cp /dev/null $@
	echo "deb http://switch-nfs.hw.bigswitch.com/export/apt/ stable main" >> $@

clean: clean-local

clean-local:
	rm -f switch-nfs.list
