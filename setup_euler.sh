#!/bin/sh

module load java/1.8.0_31
module load python/3.6.0
module load maven
module load eth_proxy

export MAVEN_OPTS="-Dhttp.proxyHost=proxy.ethz.ch -Dhttp.proxyPort=3128 -Dhttps.proxyHost=proxy.ethz.ch -Dhttps.proxyPort=3128"
