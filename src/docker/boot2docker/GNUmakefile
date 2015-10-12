######################################################################
#
# GNUmakefile for src/docker/boot2docker
#
######################################################################

DRIVER		= virtualbox
##DRIVER		= vmwarefusion

MACHINE		= some-machine

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

create-machine: GNUmakefile
	docker-machine create $(CREATE_OPTS) --driver $(DRIVER) $(MACHINE)

bootstrap: GNUmakefile docker-machine-bootstrap rc.local
	./docker-machine-bootstrap $(VOLUME_OPTS) $(MACHINE)

