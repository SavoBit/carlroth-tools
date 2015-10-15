######################################################################
#
# GNUmakefile for src/docker/boot2docker
#
######################################################################

##DOCKER_MACHINE_DRIVER		= virtualbox
##DOCKER_MACHINE_NAME		= default

DOCKER_MACHINE_DRIVER		= vmwarefusion
DOCKER_MACHINE_NAME		= fusion

CREATE_OPTS	= \
  --virtualbox-memory 8192 \
  --vmwarefusion-memory-size 8192 \
  # THIS LINE INTENTIONALLY LEFT BLANK

VOLUME_OPTS	= \
  --volume /Users \
  --volume /Volumes/data \
  --volume /Volumes/spool \
  # THIS LINE INTENTIONALLY LEFT BLANK

default:
	:

include ../../../make/config.mk
-include docker.mk

create-machine: GNUmakefile
	docker-machine create $(CREATE_OPTS) --driver $(DOCKER_MACHINE_DRIVER) $(DOCKER_MACHINE_NAME)
	test -f docker.mk || cp /dev/null docker.mk
	@: ;\
	set -e; set -x ;\
	sed -i.bak \
	  -e '/DOCKER_MACHINE_NAME/d' \
	  -e '/DOCKER_MACHINE_DRIVER/d' \
	  -e '/DOCKER_MACHINE_SSH_CONTROL_PATH/d' \
	  -e '/DOCKER_MACHINE_SSH_AGENT/d' \
	  docker.mk ;\
	eval $$(docker-machine env $(DOCKER_MACHINE_NAME)) ;\
	echo "DOCKER_MACHINE_NAME=$(DOCKER_MACHINE_NAME)" >> docker.mk ;\
	echo "DOCKER_MACHINE_DRIVER=$(DOCKER_MACHINE_DRIVER)" >> docker.mk ;\
	./docker-machine-ssh-socket --close $(DOCKER_MACHINE_NAME)
	./docker-machine-ssh-socket --create $(DOCKER_MACHINE_NAME)
	./docker-machine-ssh-socket --inspect $(DOCKER_MACHINE_NAME) >> docker.mk

bootstrap: GNUmakefile docker-machine-bootstrap rc.local
	./docker-machine-bootstrap \
	  --container-uid $(DOCKER_UID) --container-gid $(DOCKER_GID) \
	  $(VOLUME_OPTS) \
	  $(DOCKER_MACHINE_NAME)
