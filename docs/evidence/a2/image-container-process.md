# A2.1 — Image, Container, Process and Isolation Model

## Objective

Understand what Docker changes when an OpsForge service moves from a normal
host process into a container.

The goal of this subsection is not simply to make the gateway run inside
Docker.

The goal is to understand the relationship between:

```text
source code
    ↓
Dockerfile
    ↓
build context
    ↓
image
    ↓
container
    ↓
PID 1
    ↓
application process
```

A2.1 establishes the container runtime model that later A2 sections will build
on.

---

## Starting Point from A1

At the end of A1, the gateway ran directly on the host:

```text
macOS host
│
└── gateway-api
      │
      ├── Python / Uvicorn process
      ├── host PID
      ├── host filesystem
      ├── host network
      └── 127.0.0.1:8000
```

The application process shared the same host environment as:

- the shell
- `curl`
- PostgreSQL
- Redis
- inventory-api
- the worker

The host-level model was therefore:

```text
program
   ↓
execute
   ↓
process
```

A2 introduces another layer:

```text
source
   ↓
build
   ↓
image
   ↓
run
   ↓
container
   ↓
process
```

The application is still a process.

Docker changes the environment surrounding that process.

---

## Core Mental Model

A container is not a small virtual machine containing a magical application.

The application remains an ordinary running process.

Docker provides isolation around that process.

Conceptually:

```text
macOS
│
└── Docker Linux runtime
      │
      └── container
           │
           ├── isolated process view
           ├── isolated filesystem view
           ├── isolated network view
           ├── runtime environment
           └── gateway process
```

The most important A2.1 principle is:

> Docker does not replace the application process. Docker places the process
> inside an isolated and reproducible runtime environment.

---

# Image Versus Container

## Docker Image

A Docker image is a static reusable artifact.

The OpsForge gateway image contains:

```text
Python runtime
+
installed Python dependencies
+
OpsForge application source
+
filesystem contents
+
image metadata
+
default startup command
```

An image does not represent a running application.

It can exist while no corresponding container is running.

Conceptually:

```text
IMAGE
─────

static
immutable runtime template
reusable
not executing
```

---

## Docker Container

A container is a runtime instance created from an image.

Conceptually:

```text
image
   ↓
docker run
   ↓
container
   ↓
application process starts
```

Multiple containers can be created from the same image.

Therefore:

```text
image
   │
   ├── container A
   ├── container B
   └── container C
```

The image remains reusable even after individual containers are stopped or
deleted.

---

## Image and Container Lifecycle Experiment

The Docker environment was initially verified using:

```bash
docker version
```

and:

```bash
docker info
```

A basic Docker runtime test was performed with:

```bash
docker run --rm hello-world
```

The `--rm` option demonstrated that the container could disappear after the
process exited while the underlying image remained available.

The distinction is:

```text
container removed
        ≠
image removed
```

---

# Gateway Dockerfile Baseline

The initial OpsForge gateway image was built from:

```text
docker/gateway.Dockerfile
```

The baseline Dockerfile used during A2.1 was conceptually:

```dockerfile
FROM python:3.13-slim

WORKDIR /opt/opsforge

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD [
    "uvicorn",
    "app.gateway.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]
```

Later A2 sections will harden this image using:

- multi-stage builds
- non-root execution
- runtime minimization
- image-size measurement
- build-cache measurement

A2.1 intentionally began with a simple Dockerfile so that the runtime model
could be understood first.

---

# Dockerfile Instruction Model

## FROM

```dockerfile
FROM python:3.13-slim
```

The gateway image begins with an existing Python runtime image.

Conceptually:

```text
python:3.13-slim
        │
        ├── minimal Linux userspace
        ├── Python runtime
        └── Python tooling
```

OpsForge application layers are added on top of this base.

---

## WORKDIR

```dockerfile
WORKDIR /opt/opsforge
```

This establishes:

```text
/opt/opsforge
```

as the working directory inside the image and container.

This matters because Python imports and relative filesystem operations are
evaluated from the container environment rather than from the host repository.

---

## COPY

```dockerfile
COPY requirements.txt .
```

and:

```dockerfile
COPY app ./app
```

copy files from the Docker build context into the image filesystem.

This creates a snapshot of those files at build time.

The container does not automatically execute directly from the host repository.

---

## RUN

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

`RUN` executes during image construction.

Therefore:

```text
docker build
    ↓
RUN pip install
    ↓
dependencies become part of image
```

This is different from the runtime application process.

The installation step does not run every time a container starts.

---

## CMD

```dockerfile
CMD [
    "uvicorn",
    "app.gateway.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]
```

`CMD` defines the default process started when a container is created from the
image.

Conceptually:

```text
docker run
    ↓
CMD
    ↓
uvicorn
    ↓
FastAPI gateway
```

---

# Docker Build Context

The gateway image was built with:

```bash
docker build \
  -f docker/gateway.Dockerfile \
  -t opsforge-gateway:a2.1 \
  .
```

The final:

```text
.
```

is the Docker build context.

It defines the filesystem tree Docker can use for build instructions such as:

```dockerfile
COPY app ./app
```

The build context is therefore different from the Dockerfile itself.

Conceptually:

```text
Dockerfile
    │
    │ describes build
    ▼

Build context
    │
    │ supplies files
    ▼

Docker builder
    │
    ▼

Image
```

This distinction becomes important later when measuring:

- build speed
- cache invalidation
- image reproducibility
- unnecessary build context size

---

# .dockerignore

A `.dockerignore` file was added to prevent unnecessary local files from
entering the Docker build context.

Examples include:

```text
__pycache__/
*.pyc
.venv/
.git/
.pytest_cache/
.DS_Store
.env
```

This provides several benefits:

```text
smaller build context
        ↓
less unnecessary data sent to builder
        ↓
fewer accidental local artifacts
        ↓
cleaner and more reproducible image build
```

It also reduces the risk that local environment files or development artifacts
accidentally enter the runtime image.

---

# Image Immutability

One of the most important observations from A2.1 was that changing source code
on the host does not modify an already-built Docker image.

The sequence is:

```text
host source code
      ↓
docker build
      ↓
image snapshot
```

After the image exists:

```text
edit host source
      │
      X
      │
existing image does not change
```

The corrected source must be rebuilt into a new image:

```text
updated source
      ↓
docker build
      ↓
updated image
```

This establishes the image immutability mental model that later phases will use
for CI and immutable artifact promotion.

---

# Inspecting Image Metadata

The gateway image was inspected using:

```bash
docker image inspect opsforge-gateway:a2.1
```

The configured working directory was verified with:

```bash
docker image inspect \
  opsforge-gateway:a2.1 \
  --format '{{.Config.WorkingDir}}'
```

Expected value:

```text
/opt/opsforge
```

The configured startup command was verified with:

```bash
docker image inspect \
  opsforge-gateway:a2.1 \
  --format '{{json .Config.Cmd}}'
```

The image recorded the equivalent of:

```text
[
  "uvicorn",
  "app.gateway.main:app",
  "--host",
  "0.0.0.0",
  "--port",
  "8000"
]
```

This demonstrated that container startup behavior is stored as image metadata.

---

# Container Startup

The gateway container was started using:

```bash
docker run \
  --name opsforge-gateway \
  opsforge-gateway:a2.1
```

When successful, Uvicorn reported:

```text
Started server process [1]
Waiting for application startup.
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

This established that:

```text
image
   ↓
container
   ↓
Uvicorn starts
   ↓
FastAPI application starts
```

---

# PID Namespace and PID 1

One of the most important A2.1 observations was that the Uvicorn process became
PID 1 inside the container.

The process was inspected using the Linux `/proc` filesystem:

```bash
docker exec opsforge-gateway \
  sh -c 'cat /proc/1/status | head -n 8'
```

The output showed:

```text
Pid:    1
PPid:   0
```

The command line for PID 1 was inspected using:

```bash
docker exec opsforge-gateway \
  sh -c 'tr "\0" " " < /proc/1/cmdline; echo'
```

The result showed the gateway startup command:

```text
/usr/local/bin/python3.13
/usr/local/bin/uvicorn
app.gateway.main:app
--host 0.0.0.0
--port 8000
```

Therefore, inside the container:

```text
container PID namespace
        │
        ▼
PID 1
        │
        ▼
Python / Uvicorn
        │
        ▼
FastAPI gateway
```

This connects directly to A1 process concepts.

---

# Host-Side PID Versus Container PID

Docker inspection also returned a runtime-side PID using:

```bash
docker inspect opsforge-gateway \
  --format '{{.State.Pid}}'
```

The returned PID differed from PID 1 observed inside the container.

This demonstrates namespace-relative process identity.

Conceptually:

```text
Docker/runtime view
        │
        └── process PID = runtime-visible value


Container PID namespace
        │
        └── same workload appears as PID 1
```

A process identifier only has meaning relative to the namespace from which it
is observed.

On Docker Desktop for macOS, Linux containers execute inside Docker's Linux
runtime environment rather than directly as ordinary native macOS processes.

---

# Minimal Runtime Image Observation

The image uses:

```text
python:3.13-slim
```

The following command was attempted:

```bash
docker exec opsforge-gateway ps aux
```

and failed because:

```text
ps: executable file not found
```

A second attempt:

```bash
docker exec opsforge-gateway \
  sh -c 'ps -o pid,ppid,comm,args'
```

also failed.

This did not mean that no process existed.

It meant the minimal runtime image did not contain the `ps` utility.

The distinction is:

```text
process inspection utility missing
        ≠
application process missing
```

The process could still be inspected using:

```text
docker top
/proc/1/status
/proc/1/cmdline
docker inspect
```

This is an important production-container lesson.

Minimal runtime images often intentionally omit interactive troubleshooting
utilities.

---

# Container Filesystem View

The running container was entered using:

```bash
docker exec -it opsforge-gateway sh
```

The working directory was:

```text
/opt/opsforge
```

The filesystem contained the files copied during the image build.

Conceptually:

```text
host repository
      │
      │ COPY during docker build
      ▼
image filesystem
      │
      │ docker run
      ▼
container filesystem view
```

The container does not automatically share the host repository filesystem.

Bind mounts will be introduced later in A2 where appropriate.

---

# Application Binding Inside the Container

The gateway runs with:

```text
--host 0.0.0.0
--port 8000
```

Inside the container:

```text
0.0.0.0
```

means the application listens on all IPv4 interfaces available in that
container's network namespace.

This is different from:

```text
127.0.0.1
```

which refers only to the container's own loopback interface.

Conceptually:

```text
container
│
├── loopback
│      127.0.0.1
│
└── Docker network interface
       container address

0.0.0.0:8000
=
listen across available IPv4 interfaces
```

This prepares the application to receive traffic through Docker networking.

---

# Important A2.1 Network Observation

During the first successful container run, Uvicorn was listening on:

```text
0.0.0.0:8000
```

but the host could not reach:

```text
127.0.0.1:8000
```

because no Docker host port had yet been published.

The state was:

```text
container
│
└── Uvicorn :8000     ✅

host
│
└── :8000 mapping     ❌
```

This observation became the starting problem for A2.2.

A2.2 separately studies:

- container ports
- host ports
- `EXPOSE`
- `-p`
- host-to-container traffic

---

# Signal Propagation

The running gateway was stopped using:

```bash
docker stop opsforge-gateway
```

The container logs showed:

```text
Shutting down
Waiting for application shutdown.
Application shutdown complete.
Finished server process [1]
```

This demonstrated graceful application termination.

The conceptual path is:

```text
docker stop
    ↓
termination signal
    ↓
container PID 1
    ↓
Uvicorn
    ↓
FastAPI shutdown
    ↓
process exits
    ↓
container stops
```

This directly connects Docker behavior to the signal concepts established in
A1.

A later A2 subsection will examine PID 1 and signal behavior more deeply.

---

# Container State After Process Exit

After the application process stopped:

```bash
docker ps
```

no longer showed the container as running.

However:

```bash
docker ps -a
```

showed the stopped container.

This demonstrated:

```text
running process exits
        ↓
container becomes stopped/exited
```

The container object still existed until explicitly removed.

It was removed with:

```bash
docker rm opsforge-gateway
```

The image remained available.

Therefore:

```text
remove container
       ≠
remove image
```

---

# A2.1 Troubleshooting Incident

During the first image execution, the container crashed while Uvicorn attempted
to import the gateway application.

The initial traceback reported:

```text
ModuleNotFoundError: No module named 'numpy'
```

Further investigation revealed that the local OpsForge gateway source had
accidentally been overwritten with code from a separate GPU forecasting
project.

The contaminated source included imports such as:

```text
numpy
torch
gpuforecast
```

These dependencies do not belong to the OpsForge gateway.

The important diagnostic sequence was:

```text
image built successfully
        ↓
container created successfully
        ↓
Uvicorn started
        ↓
gateway Python module imported
        ↓
unexpected dependency import failed
        ↓
process exited
        ↓
container stopped
```

This showed that the failure was not initially a Docker engine failure.

Docker had faithfully packaged and attempted to execute the source present in
the build context.

---

## Git Recovery

The known-good A1 gateway was recovered from the versioned repository state
rather than reconstructed manually.

The gateway history was inspected using:

```bash
git log --oneline --follow -- app/gateway/main.py
```

The A1 release version was inspected using:

```bash
git show v0.2.0:app/gateway/main.py
```

The gateway was restored using:

```bash
git restore --source=v0.2.0 -- app/gateway/main.py
```

A subsequent:

```bash
git diff -- app/gateway/main.py
```

returned no changes, confirming that the restored file matched the committed
A1 baseline.

This demonstrated the practical value of:

- meaningful Git commits
- semantic phase tags
- continuous pushes
- known-good release checkpoints

The versioned A1 baseline prevented accidental source corruption from becoming
a permanent project change.

---

## Stale Python Cache Observation

A contamination search found an old match inside:

```text
app/gateway/__pycache__/main.cpython-313.pyc
```

This was a compiled Python cache artifact rather than current source code.

Cache files were removed using:

```bash
find app -type d -name "__pycache__" -prune -exec rm -rf {} +
```

and:

```bash
find app -type f -name "*.pyc" -delete
```

A `.dockerignore` was added so compiled caches and local development artifacts
are not included in future Docker build contexts.

---

# Clean Dependency Boundary

The troubleshooting incident exposed another useful container principle.

A local development machine may contain dependencies that are not explicitly
declared by the application.

A clean container image only contains what was deliberately installed.

Therefore containerization provides a useful dependency boundary:

```text
application import
       ↓
dependency declared and installed?
       │
       ├── yes → continue
       │
       └── no  → fail visibly
```

This helps expose hidden "works on my machine" assumptions.

However, the correct response is not always to install every missing package.

The first diagnostic question should be:

> Does this application actually require this dependency?

In the OpsForge incident, the unexpected ML dependencies belonged to the wrong
source file and were removed by restoring the correct versioned gateway code.

---

# Image Import Verification

Before starting Uvicorn again, the corrected image was tested directly using:

```bash
docker run --rm \
  opsforge-gateway:a2.1 \
  python -c "import app.gateway.main; print('container gateway import OK')"
```

Expected result:

```text
container gateway import OK
```

This separated application import verification from HTTP server startup.

The debugging layers became:

```text
1. image exists
        ↓
2. container can start
        ↓
3. Python module imports
        ↓
4. Uvicorn starts
        ↓
5. socket listens
        ↓
6. networking reaches socket
        ↓
7. HTTP application responds
```

This layered diagnostic model will continue throughout Track A.

---

# A2.1 Final Runtime Model

The final A2.1 mental model is:

```text
HOST SOURCE
    │
    ▼
Docker build context
    │
    ▼
Dockerfile instructions
    │
    ▼
IMAGE
    │
    │ static reusable artifact
    │
    ▼
docker run
    │
    ▼
CONTAINER
    │
    ├── isolated PID view
    ├── isolated filesystem view
    ├── isolated network view
    └── runtime configuration
            │
            ▼
          PID 1
            │
            ▼
      Python / Uvicorn
            │
            ▼
       FastAPI gateway
```

---

# Key Distinctions

## Program Versus Process

```text
program
=
stored executable/code

process
=
executing program
```

---

## Image Versus Container

```text
image
=
static reusable runtime artifact

container
=
runtime instance created from image
```

---

## Container Versus Process

```text
container
=
isolated runtime environment

process
=
application executing inside that environment
```

---

## Host PID Versus Container PID

```text
same workload
+
different process namespaces
=
different visible PID values
```

---

## Host Filesystem Versus Container Filesystem

```text
host repository
≠
container filesystem
```

Files enter an image through the Docker build process unless an explicit mount
is configured.

---

## Image Change Versus Source Change

```text
edit host source
≠
modify existing image
```

A rebuild is required to create a new image containing updated source.

---

# Reproducible A2.1 Commands

## Build

```bash
docker build \
  -f docker/gateway.Dockerfile \
  -t opsforge-gateway:a2.1 \
  .
```

## Inspect Image

```bash
docker image inspect \
  opsforge-gateway:a2.1 \
  --format '{{.Config.WorkingDir}}'
```

```bash
docker image inspect \
  opsforge-gateway:a2.1 \
  --format '{{json .Config.Cmd}}'
```

## Validate Gateway Import

```bash
docker run --rm \
  opsforge-gateway:a2.1 \
  python -c "import app.gateway.main; print('container gateway import OK')"
```

## Start Container

```bash
docker run \
  --name opsforge-gateway \
  opsforge-gateway:a2.1
```

## Inspect Running Containers

```bash
docker ps
```

## Inspect PID 1

```bash
docker exec opsforge-gateway \
  sh -c 'cat /proc/1/status | head -n 8'
```

## Inspect PID 1 Command

```bash
docker exec opsforge-gateway \
  sh -c 'tr "\0" " " < /proc/1/cmdline; echo'
```

## Inspect Through Docker

```bash
docker top opsforge-gateway
```

## Inspect Container Filesystem

```bash
docker exec -it opsforge-gateway sh
```

Inside:

```bash
pwd
ls
python --version
hostname
```

Then:

```bash
exit
```

## Graceful Stop

```bash
docker stop opsforge-gateway
```

## Inspect Shutdown Logs

```bash
docker logs opsforge-gateway | tail -n 20
```

## Show Stopped Container

```bash
docker ps -a --filter name=opsforge-gateway
```

## Remove Container

```bash
docker rm opsforge-gateway
```

## Verify Image Still Exists

```bash
docker images | grep opsforge
```

---

# A2.1 Evidence Summary

The experiments demonstrated:

| Observation | Result |
|---|---|
| Docker image built successfully | ✅ |
| Gateway module imported inside image | ✅ |
| Container started successfully | ✅ |
| Uvicorn became PID 1 in container namespace | ✅ |
| Container had its own filesystem view | ✅ |
| Minimal image did not contain `ps` | ✅ |
| `/proc` could inspect PID 1 | ✅ |
| Docker stop produced graceful Uvicorn shutdown | ✅ |
| Stopped container and image remained separate objects | ✅ |
| Source changes required image rebuild | ✅ |
| Incorrect source/dependency contamination was diagnosed and recovered through Git | ✅ |
| Host access without port publishing failed | ✅ expected and carried into A2.2 |

---

# A2.1 Learning Outcome

A2.1 established that Docker does not remove the systems concepts learned in
A1.

Instead, it adds isolation and packaging around those same concepts.

The central relationship is:

```text
Dockerfile
    ↓
build
    ↓
image
    ↓
run
    ↓
container
    ↓
PID 1
    ↓
application process
```

The application remains a process.

The process still:

- starts
- has a PID
- opens sockets
- receives signals
- writes output
- exits
- can fail during startup

Docker makes the runtime environment repeatable and isolated.

It does not make the underlying process behavior disappear.

---

# Transition to A2.2

A2.1 ended with the following deliberate observation:

```text
gateway container       ✅ running
Uvicorn                  ✅ listening on container :8000
host curl :8000          ❌ connection failed
```

The next question became:

> If the application is running correctly inside the container, how does a
> request from the host reach that isolated container network?

A2.2 answers that question through:

```text
container ports
EXPOSE
host ports
port publishing
-p HOST_PORT:CONTAINER_PORT
host-to-container request flow
```

A2.1 therefore establishes the process and isolation model.

A2.2 establishes how external traffic crosses that isolation boundary.
