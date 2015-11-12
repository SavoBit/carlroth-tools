######################################################################
#
# Bootstrap the floodlight container
# After the bootstrap is done, it snapshots the 'bootstrap' tag.
#
######################################################################

DOCKER_PROFILE			= floodlight
DOCKER_OS			= ubuntu:14.04

include ../../../make/config.mk

-include docker.mk

default: Dockerfile apt.conf

include ../../../make/rules.mk

# See https://bigswitch.atlassian.net/wiki/display/BSC/Development+Environment+Setup
BOOTSTRAP_PACKAGES		= \
  ssh git maven openjdk-7-jdk python-setuptools zip \
  build-essential cowbuilder python-vm-builder \
  reprepro parted gddrescue e2fsprogs mount extlinux coreutils zip debhelper zerofree \
  apt-cacher-ng \
  ccache \
  # THIS LINE INTENTIONALLY LEFT BLANK

BOOTSTRAP_PACKAGES		+= \
  python-pip \
  python-ipaddr \
  # THIS LINE INTENTIONALLY LEFT BLANK

# see https://bigswitch.atlassian.net/wiki/display/CORP/Jenkins+Server+Setup#JenkinsServerSetup-InstallOtherPrerequisitePackages

BOOTSTRAP_PACKAGES		+= \
  autoconf \
  automake \
  cowbuilder \
  curl \
  debhelper \
  gawk \
  git \
  libjson0-dev \
  libmysqlclient-dev \
  libreadline6-dev \
  libtool \
  libxslt1-dev \
  maven \
  openjdk-7-jdk \
  openjdk-7-jre \
  python-dev \
  python-mysqldb \
  python-enum \
  python-setuptools \
  python-software-properties \
  python-virtualenv \
  reprepro \
  software-properties-common \
  texinfo \
  time \
  zerofree \
  zip \
  # blank line  # THIS LINE INTENTIONALLY LEFT BLANK

BOOTSTRAP_PIP_PACKAGES		= \
  funcsigs \
  httplib2 \
  ipcalc \
  mock \
  netaddr \
  paramiko \
  pep8 \
  pexpect \
  pycrypto \
  pylint \
  pyroute2 \
  pytz \
  pyyaml \
  requests \
  "robotframework<2.8.5" \
  scp \
  setuptools \
  thrift \
  tox==1.6.1 \
  xmltodict \
  # THIS LINE INTENTIONALLY LEFT BLANK

# pre-built packages for above
BOOTSTRAP_PACKAGES		+= \
  python-ipcalc \
  python-netaddr \
  python-httplib2 \
  python-mock \
  python-paramiko \
  python-thrift \
  # THIS LINE INTENTIONALLY LEFT BLANK

bootstrap: bootstrap-floodlight

bootstrap-floodlight:
	docker exec $(DOCKER_CONTAINER_ID) sudo apt-get update
	docker exec $(DOCKER_CONTAINER_ID) sudo DEBIAN_FRONTEND=noninteractive apt-get -y install $(BOOTSTRAP_PACKAGES)
	docker exec $(DOCKER_CONTAINER_ID) sudo pip install --upgrade $(BOOTSTRAP_PIP_PACKAGES)
	docker commit $(DOCKER_CONTAINER_ID) $(DOCKER_USER)/$(DOCKER_PROFILE):bootstrap
