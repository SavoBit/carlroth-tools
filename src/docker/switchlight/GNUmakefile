######################################################################
#
# GNUmakefile for the docker floodlight stuffs
#
######################################################################

DOCKER_PROFILE			= switchlight
DOCKER_OS			= opennetworklinux/builder7:1.0

include ../../../make/config.mk

-include docker.mk

default: Dockerfile apt.conf sudoers acng.conf

DOCKER_RUN_UID			= root
# create the container as root; the docker_shell command will later drop privs

DOCKER_SHELL			= /bin/docker_shell --verbose --user "$(DOCKER_USER):$(DOCKER_UID)" -c "bash --login"
# container UID is root

include ../../../make/rules.mk

bootstrap: bootstrap-switchlight

BOOTSTRAP_PACKAGES		= \
  python-dnspython \
  python-pyroute2 \
  # THIS LINE INTENTIONALLY LEFT BLANK

bootstrap-switchlight:
	docker exec $(DOCKER_CONTAINER_ID) env DEBIAN_FRONTEND=noninteractive apt-get -y install $(BOOTSTRAP_PACKAGES)

Dockerfile: apt.conf sudoers acng.conf switch-nfs.list

switch-nfs.list:
	cp /dev/null $@
	echo "deb http://switch-nfs.hw.bigswitch.com/export/apt/ stable main" >> $@

clean: clean-local

clean-local:
	rm -f switch-nfs.list
