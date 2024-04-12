#!/usr/bin/env zsh
# vim: syntax=zsh
#
# Copyright © 2023-2024, ARCHADEPT LTD. All Rights Reserved.
# SPDX-License-Identifier: MIT
#
# This script builds a new ArchAdept CLI backend Docker image and
# optionally pushes it to DockerHub.

read -r -d '' help_message << 'EOT'
The ArchAdept CLI supports building and disassembling bare metal C and
A64 assembly projects, running those projects on a simulated Raspberry
Pi 3b, and debugging those projects using LLDB.

This works regardless of whether your host machine is x86_64 or arm64,
and regardless of whether your host operating system is Windows, Linux,
or Mac.

The ArchAdept CLI accomplishes this using Docker containers running
images that are preconfigured with all the necessary tools. This script
builds a new such image using the local ``Dockerfile`` and publishes it 
to Docker Hub, optionally making it the ``latest`` image as well.

Usage:

    build-docker-image.sh -t TAG [-l]

Parameters
==========
-t TAG
    String with which to tag the new image (example: "v3").
-l
    Make this image the ``latest`` image on Docker Hub.
EOT

#
# Underlying implementation of ``info()`` and ``err()``.
#
# Usage: ``_print [-n] stream color [message [message ...]]``
#
# Parameters
# ==========
# -n
#     May optionally be passed as the very first positional argument,
#     in which case the message will be printed without a trailing
#     newline a la ``echo -n``.
# stream
#     File number of the stream to print to: 1 for stdout, 2 for stderr.
# color
#     Xterm ``tput setaf`` color code; 1 for COLOR_RED, 2 for COLOR_GREEN,
#     3 for COLOR_YELLOW, etc.
# message
#     The string to print; may be omitted to simply print a newline a
#     la ``echo``.
#
function _print() {
	local newline=
	if [[ "$1" = "-n" ]]; then
		newline="-n"
		shift
	fi
	local stream=$1
	local color=$2
	shift 2
	local message=$@
	>&$stream echo $newline "$(tput setaf $color)${message}$(tput sgr0)"
}


#
# Print a green info message to stdout.
#
# Usage: ``info [-n] [message [message ...]]``
#
# Parameters
# ==========
# See ``_print()``.
#
function info() {
	local newline=
	if [[ "$1" = "-n" ]]; then
		newline="-n"
		shift
	fi
	local message="$@"
	_print $newline 1 2 $message
}

#
# Print a red error message to stderr.
#
# Usage: ``err [-n] [message [message ...]]``
#
# Parameters
# ==========
# See ``_print()``.
#
function err() {
	local newline=
	if [[ "$1" = "-n" ]]; then
		newline="-n"
		shift
	fi
	local message="$@"
	_print $newline 2 1 $message
}

#
# Print a red error message to stderr then abort the script.
#
# Usage: ``die [-n] [message [message ...]]``
#
# Parameters
# ==========
# See ``_print()``.
#
function die() {
	if [[ -n "$@" ]]; then
		err $@
	fi
	exit 1
}

# Parse command-line arguments.
while getopts "ht:l" opt; do
	case "${opt}" in
		t)
			image_tag="${OPTARG}"
			;;
		l)
			make_latest=1
			;;
		h)
			info "${help_message}"
			exit 0
			;;
		*)
			die
			;;
	esac
done
shift $((OPTIND - 1))
OPTIND=1
if [[ -z "$image_tag" ]]; then
	die 'missing required argument: -t TAG'
fi

image_repo="archadept"
image_name="archadeptcli-backend"
image_tag="${image_repo}/${image_name}:${image_tag}"
info "new tag is: ${image_tag}"

info "starting multi-platform Docker image build..."
if ! docker buildx build \
		--platform linux/arm64/v8,linux/amd64 \
		--tag ${image_tag} \
		--push \
		--cache-to type=local,dest=/tmp/docker-buildx-cache,mode=max \
		--cache-from type=local,src=/tmp/docker-buildx-cache \
		.; then
	die "failed to build multi-platform Docker image"
fi

if [[ $make_latest -eq 1 ]]; then
	info "making 'latest' point to '${image_tag}'..."
	if ! docker buildx imagetools create -t ${image_repo}/${image_name}:latest ${image_tag}; then
		die "failed to update 'latest' tag on Docker Hub"
	fi
fi

info "done!"

