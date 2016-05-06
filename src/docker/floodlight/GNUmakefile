######################################################################
#
# GNUmakefile for the docker floodlight stuffs
# Uses the 'bootstrap' tag created by the floodlight-bootstrap target.
#
######################################################################

DOCKER_PROFILE			= floodlight
DOCKER_OS			= roth/floodlight:bootstrap

include ../../../make/config.mk

-include docker.mk

default: Dockerfile

include ../../../make/rules.mk

eclipse:
	docker exec -i -t $(DOCKER_CONTAINER_ID) env DISPLAY=$(DISPLAY) $(HOME)/work/controller/eclipse/java-mars/eclipse/eclipse

Dockerfile: apt.conf

clean: clean-local

clean-local:
	rm -f apt.conf acng.conf
