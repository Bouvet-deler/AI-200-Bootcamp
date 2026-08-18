# Builds the tiny 'webapp:v1' image that webapp.yaml deploys.
#
# A Dockerfile is a recipe for a container image: each line adds a layer.
# We start from the official lightweight nginx image and just reconfigure it to
# listen on 8080 (to match webapp.yaml's containerPort/probes) and serve our page.

# FROM = the base image to build on. 'nginx:alpine' is nginx on tiny Alpine Linux.
FROM nginx:alpine

# COPY <src> <dest> copies a file from this build context into the image.
# Swap nginx's default site config for one that listens on 8080 instead of 80.
COPY default.conf /etc/nginx/conf.d/default.conf

# Replace nginx's default welcome page with our own index.html.
COPY index.html /usr/share/nginx/html/index.html

# EXPOSE documents the port the container listens on (informational metadata).
# The actual port is set by nginx's config above; the Service maps to this port.
EXPOSE 8080
