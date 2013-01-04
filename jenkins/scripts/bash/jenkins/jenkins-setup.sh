#!/bin/bash

aptitude update
aptitude install -y openjdk-6-jre
aptitude install -y openjdk-6-jdk
wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | apt-key add -
sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'
aptitude install -y jenkins
aptitude install -y git-core
aptitude update
aptitude -y upgrade