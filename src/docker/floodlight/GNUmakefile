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

default: Dockerfile apt.conf

include ../../../make/rules.mk

apt.conf: $(top_srcdir)/src/docker/lib/apt.conf.in GNUmakefile
	sed -e 's/@PROFILE@/$(DOCKER_PROFILE)/g' $< > $@

acng.conf: $(top_srcdir)/src/docker/lib/acng.conf.in GNUmakefile
	sed -e 's/@PROFILE@/$(DOCKER_PROFILE)/g' $< > $@

eclipse:
	docker exec -i -t $(DOCKER_CONTAINER_ID) env DISPLAY=$(DISPLAY) $(HOME)/work/controller/eclipse/java-mars/eclipse/eclipse

clean: clean-local

clean-local:
	rm -f apt.conf acng.conf
