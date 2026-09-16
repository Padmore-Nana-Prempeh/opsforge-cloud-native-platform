# A2.2 — Container Ports, Port Publishing, and Host-to-Container Networking

## Objective

Understand how traffic moves from the host machine into an application process
running inside an isolated Docker container.

This subsection focuses on the distinction between:

- application binding
- container network interfaces
- container ports
- Docker image `EXPOSE` metadata
- host ports
- Docker port publishing
- host-to-container request flow
- host port collisions
- container network isolation

The purpose is not simply to memorize:

```bash
-p 8000:8000
```

The goal is to understand exactly what problem port publishing solves.

---

# Starting Point

At the end of A2.1, the OpsForge gateway was successfully running inside a
Docker container.

The application process was:

```text
Python / Uvicorn
        │
        ▼
FastAPI gateway
```

Inside the container, Uvicorn reported:

```text
Uvicorn running on http://0.0.0.0:8000
```

The container was running successfully:

```bash
docker ps
```

showed the gateway as:

```text
Up
```

However, the following request from the host failed:

```bash
curl http://127.0.0.1:8000/health/live
```

The error was equivalent to:

```text
curl: (7) Failed to connect to 127.0.0.1 port 8000
```

This initially created an important question:

> If Uvicorn is listening on port 8000 and the container is running, why can
> the host not reach it?

That question defines A2.2.

---

# A1 Networking Model

In A1, the gateway ran directly on the host.

The networking model was:

```text
macOS host
│
├── curl process
│
└── gateway process
       │
       └── 127.0.0.1:8000
```

Because both processes shared the same host network environment:

```bash
curl http://127.0.0.1:8000
```

could connect directly to the Uvicorn listening socket.

The path was:

```text
curl
  ↓
host loopback
127.0.0.1:8000
  ↓
Uvicorn
```

Docker changes this model.

---

# Container Network Isolation

Once the gateway moved into a container, it received its own network namespace.

The system became conceptually:

```text
HOST NETWORK
────────────────────────────

macOS
127.0.0.1:8000


        Docker isolation boundary


CONTAINER NETWORK
────────────────────────────

opsforge-gateway
0.0.0.0:8000
      │
      ▼
Uvicorn
```

The host and container no longer automatically share the same listening
sockets.

Therefore:

```text
container port 8000
        ≠
host port 8000
```

This is the central A2.2 distinction.

---

# Understanding 127.0.0.1 Inside a Container

In A1:

```text
127.0.0.1
=
the host machine
```

Inside a container:

```text
127.0.0.1
=
that container itself
```

The gateway container has its own loopback interface.

Conceptually:

```text
gateway container
│
├── 127.0.0.1
│      loopback inside gateway container
│
└── Docker network interface
       container network address
```

Therefore a service binding only to:

```text
127.0.0.1:8000
```

inside a container would only listen on the container's own loopback
interface.

---

# Why Uvicorn Uses 0.0.0.0

The gateway container starts Uvicorn with:

```text
--host 0.0.0.0
--port 8000
```

Inside the container:

```text
0.0.0.0
```

means:

> Listen on all available IPv4 interfaces inside this container's network
> namespace.

Conceptually:

```text
container
│
├── loopback interface
│      127.0.0.1
│
└── Docker network interface
       container address

Uvicorn
   ↓
0.0.0.0:8000
```

This allows traffic arriving through the Docker network interface to reach
Uvicorn.

However:

```text
0.0.0.0:8000 inside container
```

does not automatically mean:

```text
0.0.0.0:8000 on host
```

These belong to different network namespaces.

---

# Three Different Networking Concepts

A2.2 established that three separate ideas must not be confused.

## 1. Application Binding

The application creates a listening socket:

```text
Uvicorn
0.0.0.0:8000
```

This happens inside the container.

---

## 2. Image Port Metadata

The Dockerfile may declare:

```dockerfile
EXPOSE 8000
```

This records that the image is expected to use port 8000.

It does not automatically make the port reachable from the host.

---

## 3. Runtime Port Publishing

Docker may publish a host port using:

```bash
-p 8000:8000
```

This creates the host-to-container network mapping.

Therefore:

```text
application bind
        ≠
EXPOSE
        ≠
port publishing
```

These are related but separate layers.

---

# Experiment 1 — Run Without Port Publishing

The gateway was started without any `-p` option:

```bash
docker run \
  --name opsforge-gateway \
  opsforge-gateway:a2.1
```

The container remained healthy.

Uvicorn reported:

```text
Uvicorn running on http://0.0.0.0:8000
```

The running container was confirmed with:

```bash
docker ps
```

However:

```bash
docker port opsforge-gateway
```

returned no published host port.

The host request:

```bash
curl http://127.0.0.1:8000/health/live
```

failed.

This proved:

```text
application running inside container
        ✅

container port listening
        ✅

host port published
        ❌

host connectivity
        ❌
```

A listening container port is not automatically a listening host port.

---

# Experiment 2 — Publish Host Port 8000

The container was stopped and removed:

```bash
docker stop opsforge-gateway
docker rm opsforge-gateway
```

It was then started with:

```bash
docker run \
  --name opsforge-gateway \
  -p 8000:8000 \
  opsforge-gateway:a2.1
```

The syntax is:

```text
-p HOST_PORT:CONTAINER_PORT
```

Therefore:

```text
-p 8000:8000

host port       container port
   8000     →       8000
```

Docker then reported a mapping similar to:

```text
0.0.0.0:8000->8000/tcp
[::]:8000->8000/tcp
```

The host request:

```bash
curl -i http://127.0.0.1:8000/health/live
```

returned:

```text
HTTP/1.1 200 OK
```

with:

```json
{"status":"alive"}
```

This proved that Docker port publishing created the missing connection between
the host network and the isolated container network.

---

# Host-to-Container Request Flow

The successful request path became:

```text
curl process
      │
      ▼
host loopback
127.0.0.1:8000
      │
      ▼
Docker published-port mapping
      │
      ▼
container network namespace
      │
      ▼
container port 8000
      │
      ▼
Uvicorn listening socket
      │
      ▼
FastAPI
/health/live
      │
      ▼
HTTP 200 response
```

Compared with A1:

```text
A1

curl
 ↓
host socket :8000
 ↓
Uvicorn
```

A2 now adds another layer:

```text
A2

curl
 ↓
host socket :8000
 ↓
Docker port publishing
 ↓
container network
 ↓
container socket :8000
 ↓
Uvicorn
```

---

# Experiment 3 — Host Port and Container Port Do Not Need to Match

The gateway container was restarted using:

```bash
docker run \
  --name opsforge-gateway \
  -p 8080:8000 \
  opsforge-gateway:a2.2
```

The mapping became:

```text
host :8080
    ↓
Docker
    ↓
container :8000
```

Inside the container, Uvicorn still listened on:

```text
8000
```

The application configuration did not change.

The old host address:

```bash
curl http://127.0.0.1:8000/health/live
```

did not reach this container mapping.

The correct host request became:

```bash
curl http://127.0.0.1:8080/health/live
```

and returned HTTP 200.

This demonstrated:

```text
host port
        ≠
container port
```

The two port numbers may be different.

---

# Inspecting the Mapping

The runtime mapping was inspected using:

```bash
docker port opsforge-gateway
```

For the `8080:8000` experiment, Docker reported conceptually:

```text
8000/tcp -> 0.0.0.0:8080
```

This means:

```text
container listens on 8000
host exposes it through 8080
```

The application itself does not need to know which host port Docker uses.

---

# Why This Separation Matters

Separating host and container ports allows different runtime environments to
use different external addresses without changing application code.

For example:

```text
Development:

host :8080
   ↓
container :8000


Another environment:

host :9000
   ↓
container :8000
```

The application continues using:

```text
container port 8000
```

in both cases.

This separates:

```text
application configuration
```

from:

```text
runtime networking configuration
```

---

# Experiment 4 — Host Port Collision

A container was left running with:

```text
host :8080
    ↓
container :8000
```

A second gateway container was then started while attempting to publish the
same host port:

```bash
docker run \
  --name opsforge-gateway-two \
  -p 8080:8000 \
  opsforge-gateway:a2.2
```

Docker rejected the request because host port `8080` was already allocated.

This connects directly to A1 socket ownership.

Conceptually:

```text
host :8080
    │
    └── already owned by first Docker mapping

second mapping requests host :8080
    ↓
collision
    ↓
failure
```

A host port cannot normally be simultaneously owned by two independent
listeners/mappings on the same host address.

---

# Experiment 5 — Two Containers Can Use the Same Internal Port

The second container was instead started using:

```bash
docker run \
  --name opsforge-gateway-two \
  -p 8081:8000 \
  opsforge-gateway:a2.2
```

This created:

```text
host :8080
    ↓
container A :8000


host :8081
    ↓
container B :8000
```

Both containers used:

```text
internal port 8000
```

without conflict.

This works because each container has its own network namespace.

Conceptually:

```text
container A network namespace
└── :8000


container B network namespace
└── :8000
```

The two sockets exist in separate network environments.

---

# Network Namespace Isolation

Without container isolation, two host processes attempting to bind the same
host address and port could collide.

With container network namespaces:

```text
container A
127.x / container-interface
:8000


container B
127.x / container-interface
:8000
```

each container has its own isolated network stack.

Therefore:

```text
same internal port
+
different container network namespaces
=
no conflict
```

The conflict only appears when both containers attempt to publish the same host
port.

---

# EXPOSE

The Dockerfile was updated to include:

```dockerfile
EXPOSE 8000
```

The image was rebuilt:

```bash
docker build \
  -f docker/gateway.Dockerfile \
  -t opsforge-gateway:a2.2 \
  .
```

Image metadata was inspected using:

```bash
docker image inspect \
  opsforge-gateway:a2.2 \
  --format '{{json .Config.ExposedPorts}}'
```

The image reported:

```text
{"8000/tcp":{}}
```

This demonstrated that:

```dockerfile
EXPOSE 8000
```

creates image metadata describing the intended application port.

---

# EXPOSE Does Not Publish the Port

The rebuilt image was started without `-p`:

```bash
docker run \
  --name opsforge-gateway \
  opsforge-gateway:a2.2
```

The container was running and the image declared:

```text
8000/tcp
```

However:

```bash
curl http://127.0.0.1:8000/health/live
```

still failed from the host.

This proved:

```text
EXPOSE
        ≠
host port publishing
```

`EXPOSE` describes intended container networking behavior.

It does not automatically create a host-to-container mapping.

---

# EXPOSE Versus -p

The distinction established in A2.2 is:

```text
EXPOSE 8000
```

means:

> This image expects the application to use container port 8000.

While:

```text
-p 8000:8000
```

means:

> Publish host port 8000 and forward traffic to container port 8000.

Therefore:

```text
EXPOSE
=
image metadata


-p
=
runtime networking configuration
```

---

# Application Socket Still Matters

Neither `EXPOSE` nor `-p` causes the application itself to listen.

The actual listening socket is created by Uvicorn.

Therefore this could happen:

```text
Dockerfile
EXPOSE 8000
        ✅

Docker runtime
-p 8000:8000
        ✅

Uvicorn process
not running
        ❌
```

The result would still be an unavailable application.

The full system requires:

```text
running application process
        +
listening socket
        +
correct interface binding
        +
Docker port publishing
        =
host connectivity
```

---

# Uppercase -P

Docker also supports:

```bash
-P
```

This publishes ports declared with `EXPOSE` using automatically selected host
ports.

Example:

```bash
docker run \
  --name opsforge-random-port \
  -P \
  opsforge-gateway:a2.2
```

The mapping can be inspected with:

```bash
docker port opsforge-random-port
```

Docker may return something conceptually similar to:

```text
8000/tcp -> 0.0.0.0:55031
```

The exact host port is selected dynamically.

This is useful for understanding Docker behavior, although OpsForge will use
predictable networking configuration for its normal local environment.

---

# Explicit Host Bind Address

A published port may also specify the host address.

Example:

```bash
docker run \
  --name opsforge-gateway \
  -p 127.0.0.1:8000:8000 \
  opsforge-gateway:a2.2
```

The syntax becomes:

```text
HOST_ADDRESS:HOST_PORT:CONTAINER_PORT
```

Therefore:

```text
127.0.0.1 : 8000 : 8000
     │        │       │
     │        │       └── container port
     │        └────────── host port
     └─────────────────── host address
```

This binds the published service specifically to the host loopback interface.

For a local development environment, this can reduce unnecessary exposure
compared with binding to all host interfaces.

---

# Docker ps Port Output

When the container was started using:

```bash
-p 8000:8000
```

`docker ps` displayed:

```text
0.0.0.0:8000->8000/tcp
[::]:8000->8000/tcp
```

This can be interpreted as:

```text
host IPv4 interfaces :8000
              ↓
container :8000
```

and:

```text
host IPv6 interfaces :8000
              ↓
container :8000
```

This Docker runtime mapping must not be confused with Uvicorn's own:

```text
0.0.0.0:8000
```

The two occur at different networking layers.

---

# Networking Layers

The complete A2.2 model contains several separate layers:

```text
Layer 1
Application
───────────
Uvicorn binds
0.0.0.0:8000


Layer 2
Container Network
─────────────────
container owns isolated
network interfaces


Layer 3
Docker Runtime
──────────────
-p HOST:CONTAINER
creates mapping


Layer 4
Host Network
────────────
curl connects to
127.0.0.1:HOST_PORT
```

A failure can occur independently at any one of these layers.

---

# Troubleshooting Model

A2.2 established a systematic container networking diagnostic sequence.

## Step 1 — Is the container running?

```bash
docker ps
```

If the container is not running, host networking cannot reach the application.

---

## Step 2 — Is the application process running?

Possible tools include:

```bash
docker top opsforge-gateway
```

or:

```bash
docker logs opsforge-gateway
```

or inspection through:

```text
/proc/1
```

---

## Step 3 — What address and port does the application bind?

For OpsForge:

```text
0.0.0.0:8000
```

This was visible in Uvicorn logs.

---

## Step 4 — Is a host port published?

```bash
docker port opsforge-gateway
```

If no mapping exists, the host should not be expected to reach the service
through its own port.

---

## Step 5 — Which host port is published?

For example:

```text
8000/tcp -> 0.0.0.0:8080
```

means the correct host port is:

```text
8080
```

not:

```text
8000
```

---

## Step 6 — Test the TCP/HTTP path

```bash
curl -i http://127.0.0.1:8080/health/live
```

---

## Step 7 — Distinguish Network Failure from HTTP Failure

A connection failure such as:

```text
Failed to connect
```

occurs before an HTTP response exists.

An HTTP result such as:

```text
404
503
500
```

means the network path succeeded far enough for the application to return an
HTTP response.

This distinction continues the layered failure reasoning introduced in A1.

---

# Deliberate Failure Experiment

A healthy gateway container was started with:

```bash
docker run \
  --name opsforge-gateway \
  -p 127.0.0.1:8000:8000 \
  opsforge-gateway:a2.2
```

The request:

```bash
curl http://127.0.0.1:8000/health/live
```

returned successfully.

The container was then stopped:

```bash
docker stop opsforge-gateway
```

The same request then failed.

Inspection with:

```bash
docker ps
```

showed that the container was no longer running.

Inspection with:

```bash
docker ps -a \
  --filter name=opsforge-gateway
```

showed the container in an exited state.

This demonstrated:

```text
configured port mapping
        ≠
running application
```

A published port only becomes useful when a running process exists behind it.

---

# Port Publishing Does Not Replace Process Health

The complete dependency chain is:

```text
host request
     ↓
host port
     ↓
Docker published mapping
     ↓
container network
     ↓
container port
     ↓
application listening socket
     ↓
application process
```

If any layer is missing, connectivity fails.

Examples:

```text
container stopped
        → fail

application crashed
        → fail

wrong host port
        → fail

no published mapping
        → fail

application bound only to wrong interface
        → fail
```

This reinforces the layered troubleshooting model used throughout OpsForge.

---

# Relationship to Kubernetes

A2.2 introduces concepts that will later appear again in Kubernetes.

Docker currently provides:

```text
container port
host publication
container network namespace
```

Later Kubernetes introduces concepts such as:

```text
containerPort
Pod networking
Service
ClusterIP
Ingress / LoadBalancer
```

The abstractions change, but the underlying question remains:

> Which socket is listening, in which network namespace, and how does traffic
> reach it?

Understanding Docker networking first makes the Kubernetes networking model
easier to reason about later.

---

# Key Distinctions

## 0.0.0.0 Versus 127.0.0.1

```text
127.0.0.1
=
loopback within the current network namespace


0.0.0.0
=
listen across available IPv4 interfaces
within the current network namespace
```

---

## Container Port Versus Host Port

```text
container :8000
        ≠
host :8000
```

A runtime mapping is required to connect them.

---

## EXPOSE Versus Publish

```text
EXPOSE 8000
=
image metadata


-p 8000:8000
=
runtime host-to-container mapping
```

---

## Application Binding Versus Docker Mapping

```text
Uvicorn 0.0.0.0:8000
=
application listening behavior


Docker -p 8000:8000
=
external runtime network configuration
```

---

## Internal Port Reuse Versus Host Port Collision

```text
container A :8000
container B :8000
=
valid
```

because their network namespaces differ.

But:

```text
container A requests host :8080
container B requests host :8080
=
collision
```

---

# Reproducible A2.2 Commands

## Run Without Publishing

```bash
docker run \
  --name opsforge-gateway \
  opsforge-gateway:a2.2
```

Inspect:

```bash
docker port opsforge-gateway
```

Test:

```bash
curl http://127.0.0.1:8000/health/live
```

Expected:

```text
host connection fails
```

---

## Publish Matching Port

```bash
docker run \
  --name opsforge-gateway \
  -p 8000:8000 \
  opsforge-gateway:a2.2
```

Test:

```bash
curl -i http://127.0.0.1:8000/health/live
```

Expected:

```text
HTTP/1.1 200 OK
```

---

## Publish Different Host Port

```bash
docker run \
  --name opsforge-gateway \
  -p 8080:8000 \
  opsforge-gateway:a2.2
```

Inspect:

```bash
docker port opsforge-gateway
```

Test:

```bash
curl -i http://127.0.0.1:8080/health/live
```

---

## Attempt Host-Port Collision

With one container already using host port `8080`:

```bash
docker run \
  --name opsforge-gateway-two \
  -p 8080:8000 \
  opsforge-gateway:a2.2
```

Expected:

```text
Docker rejects duplicate host port allocation
```

---

## Use Separate Host Ports

```bash
docker run \
  --name opsforge-gateway-two \
  -p 8081:8000 \
  opsforge-gateway:a2.2
```

Result:

```text
host :8080 -> container A :8000
host :8081 -> container B :8000
```

---

## Inspect EXPOSE Metadata

```bash
docker image inspect \
  opsforge-gateway:a2.2 \
  --format '{{json .Config.ExposedPorts}}'
```

---

## Publish EXPOSE Ports Automatically

```bash
docker run \
  --name opsforge-random-port \
  -P \
  opsforge-gateway:a2.2
```

Inspect:

```bash
docker port opsforge-random-port
```

---

## Bind Only to Host Loopback

```bash
docker run \
  --name opsforge-gateway \
  -p 127.0.0.1:8000:8000 \
  opsforge-gateway:a2.2
```

---

# A2.2 Evidence Summary

| Experiment | Result |
|---|---|
| Gateway listens on `0.0.0.0:8000` inside container | ✅ |
| Container runs without host port publishing | ✅ |
| Host cannot reach unpublished container port | ✅ |
| `-p 8000:8000` enables host connectivity | ✅ |
| `/health/live` returns HTTP 200 through published port | ✅ |
| Host port and container port can differ | ✅ |
| `8080:8000` mapping verified | ✅ |
| Two containers can use internal port 8000 | ✅ |
| Duplicate host port publishing causes collision | ✅ |
| `EXPOSE 8000` stored as image metadata | ✅ |
| `EXPOSE` alone does not publish host port | ✅ |
| `-P` can allocate a dynamic host port | ✅ |
| Explicit loopback host binding demonstrated | ✅ |
| Stopping container removes usable network path | ✅ |
| Docker mapping does not replace application process health | ✅ |

---

# A2.2 Learning Outcome

A2.2 established that container networking introduces a boundary between the
host network and the application's container network.

The central request path is:

```text
host application
      ↓
host address + host port
      ↓
Docker port publishing
      ↓
container network namespace
      ↓
container port
      ↓
application listening socket
```

The most important distinctions are:

```text
0.0.0.0 inside container
        ≠
host 0.0.0.0


container port
        ≠
host port


EXPOSE
        ≠
publish


port mapping
        ≠
running application
```

Docker isolates networking.

Port publishing deliberately creates a path across that isolation boundary.

---

# Transition to A2.3

A2.2 solved:

> How does the host reach a service inside a container?

The next question is different:

> How does one container reach another container?

The next topology will introduce:

```text
gateway container
        │
        │ HTTP
        ▼
inventory container
```

The A1 configuration:

```text
http://127.0.0.1:8001
```

will no longer mean:

```text
inventory-api
```

from inside the gateway container.

Instead:

```text
127.0.0.1
```

inside the gateway means:

```text
the gateway container itself
```

A2.3 therefore introduces:

```text
Docker bridge networks
container-to-container communication
service names
Docker DNS
network aliases
internal service addressing
```

The next major lesson is:

```text
gateway
   ↓
http://inventory:8001
```

rather than:

```text
gateway
   ↓
http://127.0.0.1:8001
```

This is the foundation for service discovery concepts that will later reappear
in Kubernetes.
