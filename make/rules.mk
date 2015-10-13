##############################
#
# rules.mk
#
##############################

Dockerfile: Dockerfile.in GNUmakefile
	sed \
	  -e "s|@IMAGE@|$(DOCKER_OS)|g" \
	  -e "s|@USER@|$(DOCKER_USER)|g" \
	  -e "s|@UID@|$(DOCKER_UID)|g" \
	  -e "s|@GID@|$(DOCKER_GID)|g" \
	  -e "s|@HOME@|$(DOCKER_HOME)|g" \
	  Dockerfile.in > $@

apt.conf: GNUmakefile
	mkdir -p $(DOCKER_TMPDIR)/apt/cache/archives/partial
	mkdir -p $(DOCKER_TMPDIR)/apt/lib/lists/partial
	cp /dev/null $@
	echo "dir::cache \"$(DOCKER_TMPDIR)/apt/cache\";" >> $@
	echo "dir::state \"$(DOCKER_TMPDIR)/apt/lib\";" >> $@
	echo "acquire::http::proxy \"http://apt-proxy.eng.bigswitch.com:3142\";" >> $@
	echo "debug::nolocking 1;" >> $@

sudoers: GNUmakefile
	echo "roth    ALL=(ALL:ALL) NOPASSWD:ALL" >> $@

acng.conf.dist: /etc/apt-cacher-ng/acng.conf GNUmakefile
	mkdir -p $(DOCKER_TMPDIR)/apt-cacher-ng
	cp $< $@
	sed \
	  -e "s|^CacheDir: .*|CacheDir: $(DOCKER_TMPDIR)/apt-cacher-ng|" \
	  -e "s|^LogDir: .*|LogDir: $(DOCKER_TMPDIR)|" \
	  /etc/apt-cacher-ng/acng.conf > $@
	if test "$(http_proxy)"; then
	  echo "Proxy: $(http_proxy)" >> $@
	fi

acng.conf: GNUmakefile
	mkdir -p $(DOCKER_TMPDIR)/apt-cacher-ng
	cp /dev/null $@
	echo "Port: 3142" >> $@
	echo "LogDir: $(DOCKER_TMPDIR)" >> $@
	echo "CacheDir: $(DOCKER_TMPDIR)/apt-cacher-ng" >> $@
	echo "ForeGround: 1" >> $@
ifdef http_proxy
	echo "Proxy: $(http_proxy)" >> $@
endif

clean-images:
	@set -e; set -x ;\
	l="$(DOCKER_CONTAINER_ID) $(DOCKER_HOST_CONTAINER_ID)"; for e in $$l; do \
	  if docker inspect "$$e" 1>/dev/null 2>&1; then \
	    docker kill "$$e" || : ;\
	    docker rm "$$e" || : ;\
	  fi \
	done
	@set -e; set -x ;\
	l="$(DOCKER_IMAGE)"; for e in $$l; do \
	  if docker inspect "$$e" 1>/dev/null 2>&1; then \
	    docker rmi -f $$e || : ;\
	  fi ;\
	done
	-docker ps -a --no-trunc | grep $(DOCKER_CONTAINER) | xargs docker rm

create-images: Dockerfile apt.conf sudoers acng.conf
	docker run \
	  --detach \
	  --user root \
	  --name $(DOCKER_HOST_CONTAINER) \
	  $(DOCKER_HOST_VOLUMES) \
	  $(DOCKER_OS) \
	  /bin/true \
	> dockerid
	@set -e; set -x ;\
	id=$$(cat dockerid) ;\
	sed -i -e '/DOCKER_HOST_CONTAINER_ID/d' docker.mk || : ;\
	echo "DOCKER_HOST_CONTAINER_ID=$$id" >> docker.mk
	docker build -t $(DOCKER_IMAGE) .

ifeq ($(shell uname -s),Darwin)
SSH_AUTH_REAL	= $(shell python -c "import os; print os.path.realpath(os.environ['SSH_AUTH_SOCK']);")
else
SSH_AUTH_REAL	= $(shell realpath $(SSH_AUTH_SOCK))
endif

SSH_AUTH_DIR	= $(shell dirname $(SSH_AUTH_REAL))

DOCKER_RUN_OPTS	= \
  --detach \
  --privileged --net host \
  -t -i \
  --user $(DOCKER_UID) \
  -w $(PWD) \
  -v $(SSH_AUTH_DIR):$(SSH_AUTH_DIR) \
  -e SSH_AUTH_SOCK=$(SSH_AUTH_REAL) \
  # THIS LINE INTENTIONALLY LEFT BLANK

run:
	docker run \
	  $(DOCKER_RUN_OPTS) \
	  --volumes-from $(DOCKER_HOST_CONTAINER) \
	  --name $(DOCKER_CONTAINER) \
	  -e DOCKER_CONTAINER=$(DOCKER_IMAGE) \
	  -e DOCKER_IMAGE=$(DOCKER_IMAGE) \
	  $(DOCKER_IMAGE) \
	> dockerid
	@set -e; set -x ;\
	id=$$(cat dockerid) ;\
	sed -i.bak -e '/DOCKER_CONTAINER_ID/d' docker.mk || : ;\
	echo "DOCKER_CONTAINER_ID=$$id" >> docker.mk
	$(MAKE) bootstrap

bootstrap:
	:

shell:
	docker exec -i -t $(DOCKER_CONTAINER_ID) bash -login

clean:
	rm -f Dockerfile apt.conf acng.conf
