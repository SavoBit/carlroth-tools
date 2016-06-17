######################################################################
#
# docker-onlbuilder.mk
#
# common makefile goop for onlbuilder targets
#
######################################################################

default: Dockerfile 

DOCKER_RUN_UID			= root
# create the container as root; the docker_shell command will later drop privs

DOCKER_SHELL			= /bin/docker_shell --verbose --user "$(DOCKER_USER):$(DOCKER_UID)" -c "bash --login"
# container UID is root

include $(top_srcdir)/make/rules.mk

bootstrap: bootstrap-local

BOOTSTRAP_PACKAGES		= \
  python-dnspython \
  # THIS LINE INTENTIONALLY LEFT BLANK

##BOOTSTRAP_PACKAGES		+= \
##  python-pyroute2 \
##  # THIS LINE INTENTIONALLY LEFT BLANK

bootstrap-local:
	docker exec $(DOCKER_CONTAINER_ID) env DEBIAN_FRONTEND=noninteractive apt-get -y install $(BOOTSTRAP_PACKAGES)

Dockerfile: apt.conf sudoers acng.conf switch-nfs.list

switch-nfs.list: GNUmakefile
	cp /dev/null $@
	echo "deb http://switch-nfs.hw.bigswitch.com/export/apt/ stable main" >> $@

clean: clean-local

clean-local:
	rm -f switch-nfs.list apt.conf acng.conf
