######################################################################
#
# Attempt to set up an apt-cacher-ng appliance
#
# Starts up fine, but docker-machine+fusion does not publish port info.
# Also, --net-host doesn't work with linked containers
#
######################################################################

DOCKER_PROFILE			= acng
DOCKER_OS			= roth/floodlight:bootstrap

include ../../../make/config.mk

-include docker.mk

default: Dockerfile apt.conf acng.conf docker-init.sh

include ../../../make/rules.mk

# ha ha, doesn't really work with docker-machine/fusion
DOCKER_RUN_OPTS 		+= \
  -p 127.0.0.1::3142 \
  # THIS LINE INTENTIONALLY LEFT BLANK

docker-init.sh: docker-init.sh.in
	sed \
	  -e "s|@DOCKER_TMPDIR@|$(DOCKER_TMPDIR)|g" \
	  $< > $@
	chmod +x docker-init.sh

clean: clean-local

clean-local:
	rm -f docker-init.sh

create-images: create-images-local docker-init.sh acng.conf

create-images-local:
	cp acng.conf $(DOCKER_TMPDIR)/acng.conf
