# Deployment version

This directory contains a more complete and modular version of the Hurakan system, organized as a small multi-service application.

## Overview
- `core_app`: Flask frontend for authentication and map serving.
- `services`: backend processing, clustering, classifier, utilities, evaluation, and downscaling modules.
- `nginx`: reverse-proxy configuration.
- `testing`: manual test and utility entry points.
- `docker-compose.yml`: orchestration for the full stack.
- `.env.example`: example environment configuration.

## User manual
See [Manual](./usermanual.md) for detailed instructions to use Hurakán.

## App files stucture
See [File Structure](./filestructure.md) for visualizing the file organization for Hurakán.

