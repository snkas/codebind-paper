#!/bin/bash

NS3_VERSION="ns-3.33"

# Unzip into ns-3 temporary folder (kept to speed-up future builds)
unzip -nq ${NS3_VERSION}.zip || exit 1

# Synchronize (restores all ns-3 default files!)
rsync -ravh \
--exclude "src/antenna" \
--exclude "src/aodv" \
--exclude "src/brite" \
--exclude "src/buildings" \
--exclude "src/click" \
--exclude "src/csma" \
--exclude "src/csma-layout" \
--exclude "src/dsdv" \
--exclude "src/dsr" \
--exclude "src/energy" \
--exclude "src/fd-net-device" \
--exclude "src/flow-monitor" \
--exclude "src/internet-apps" \
--exclude "src/lr-wpan" \
--exclude "src/lte" \
--exclude "src/mesh" \
--exclude "src/mobility" \
--exclude "src/netanim" \
--exclude "src/nix-vector-routing" \
--exclude "src/olsr" \
--exclude "src/openflow" \
--exclude "src/point-to-point-layout" \
--exclude "src/propagation" \
--exclude "src/sixlowpan" \
--exclude "src/spectrum" \
--exclude "src/tap-bridge" \
--exclude "src/test" \
--exclude "src/topology-read" \
--exclude "src/uan" \
--exclude "src/virtual-net-device" \
--exclude "src/wave" \
--exclude "src/wifi" \
--exclude "src/wimax" \
${NS3_VERSION}/ ns-3/ || exit 1

# Go into ns-3 folder
cd ns-3 || exit 1

# Configure the build
./waf configure --build-profile=optimized --enable-mpi --out=build/optimized || exit 1

# Perform the build
./waf -j2 || exit 1
