# A2.4 — Container Storage, Bind Mounts, Named Volumes, and PostgreSQL Persistence

## Objective

Understand how Docker separates container lifecycle from data lifecycle and
prove, experimentally, which data survives when containers are stopped,
deleted, and recreated.

This subsection focuses on:

* container writable storage,
* bind mounts,
* Docker-managed named volumes,
* PostgreSQL persistent state,
* stop/start versus delete/recreate behavior,
* explicit versus automatically managed storage,
* network identity versus storage identity,
* and the relationship between disposable compute and durable data.

The main question is:

> If a container disappears, what happens to the data that application created?

A2.4 demonstrates that the answer depends on where the data is stored.

---

# Starting Point

Before A2.4, OpsForge already had two containerized application services:

```text
opsforge-gateway
opsforge-inventory
```

The running containers were visible with:

```bash
docker ps -a
```

The relevant services included:

```text
opsforge-inventory
    image: opsforge-inventory:a2.3
    port: 8001/tcp

opsforge-gateway
    image: opsforge-gateway:a2.2
    port mapping: 127.0.0.1:8000->8000/tcp
```

At this stage:

```text
gateway
    ↓
Docker DNS / bridge network
    ↓
inventory
```

was already functioning.

A2.4 extended the architecture with:

```text
PostgreSQL
```

and persistent storage.

---

# Core Storage Mental Model

Docker separates several concepts that must not be confused:

```text
IMAGE
    ↓
static reusable filesystem layers


CONTAINER
    ↓
runtime instance of image
    ↓
temporary writable layer


BIND MOUNT
    ↓
host-managed filesystem path


NAMED VOLUME
    ↓
Docker-managed persistent storage
```

The most important distinction for A2.4 is:

```text
container lifecycle
        ≠
data lifecycle
```

A container can disappear while explicitly managed persistent storage remains.

---

# Container Writable Layer

When a container is created from an image, Docker provides a writable layer
above the image filesystem.

Conceptually:

```text
┌─────────────────────────────┐
│ Container writable layer    │
├─────────────────────────────┤
│ Image layer                 │
├─────────────────────────────┤
│ Image layer                 │
├─────────────────────────────┤
│ Base image                  │
└─────────────────────────────┘
```

Files written only into a container's own writable filesystem are associated
with that container's lifecycle.

This is appropriate for temporary runtime state.

It is not the desired storage model for durable PostgreSQL data.

---

# Stop Versus Remove

A2.4 distinguishes two different lifecycle operations.

## Stop

```bash
docker stop <container>
```

stops the running process but preserves the container object.

Conceptually:

```text
process
   ↓
stopped

container
   ↓
still exists
```

The same container may later be restarted.

---

## Remove

```bash
docker rm <container>
```

removes the container object.

The stronger persistence test is therefore:

```text
delete container
      ↓
create a different container
      ↓
reattach same storage
      ↓
verify data still exists
```

This proves storage independence from one particular container.

---

# Experiment 1 — Host-to-Container Bind Mount

A temporary host directory was created:

```bash
rm -rf /tmp/opsforge-bind-demo
mkdir -p /tmp/opsforge-bind-demo
```

A file was created directly on the Mac host:

```bash
echo "created on the Mac Host" \
  > /tmp/opsforge-bind-demo/host.txt
```

The host verified:

```bash
cat /tmp/opsforge-bind-demo/host.txt
```

Result:

```text
created on the Mac Host
```

This established the host-side source data.

---

# Mounting the Host Directory into a Container

The host directory was mounted into an Alpine container:

```bash
docker run --rm \
  -v /tmp/opsforge-bind-demo:/data \
  alpine:3.22 \
  sh -c 'ls -la /data && cat /data/host.txt'
```

Because `alpine:3.22` was not yet available locally, Docker first pulled the
image.

The container then showed:

```text
host.txt
```

and printed:

```text
created on the Mac Host
```

This demonstrated:

```text
Mac host
/tmp/opsforge-bind-demo
       │
       │ bind mount
       ▼
container
/data
```

The file was not copied into a new image layer.

The container was directly viewing the mounted host directory.

---

# Experiment 2 — Container-to-Host Bind Mount Write

A second temporary Alpine container wrote a file into the mounted directory:

```bash
docker run --rm \
  -v /tmp/opsforge-bind-demo:/data \
  alpine:3.22 \
  sh -c 'echo "created by container" > /data/container.txt'
```

The Mac then read:

```bash
cat /tmp/opsforge-bind-demo/container.txt
```

Result:

```text
created by container
```

This proved that the bind mount was visible in both directions.

```text
HOST FILESYSTEM
      ↕
BIND MOUNT
      ↕
CONTAINER
```

---

# Bind Mount Persistence After Container Removal

Both Alpine experiments used:

```text
--rm
```

Therefore their temporary containers were automatically deleted after the
commands completed.

However:

```bash
ls -la /tmp/opsforge-bind-demo
```

still showed:

```text
host.txt
container.txt
```

The observed files were:

```text
host.txt       24 bytes
container.txt  21 bytes
```

This proved:

```text
temporary container deleted
        ↓

host directory remains
        ↓

bind-mounted files remain
```

The persistence belonged to the host filesystem, not to the removed container.

---

# Bind Mount Mental Model

The bind-mount experiment established:

```text
HOST PATH
   │
   └────── directly mounted ──────┐
                                  ▼
                              CONTAINER
```

The host owns the storage.

This makes bind mounts useful for:

```text
development source
local configuration
host-managed files
interactive development workflows
```

However, they couple the runtime to a particular host filesystem path.

For database persistence, OpsForge next tested Docker-managed named volumes.

---

# Creating the PostgreSQL Named Volume

A named volume was created:

```bash
docker volume create opsforge-postgres-data
```

Docker returned:

```text
opsforge-postgres-data
```

The volume list showed:

```text
local     opsforge-postgres-data
```

alongside unrelated volumes from other local projects.

The volume was inspected using:

```bash
docker volume inspect opsforge-postgres-data
```

The important properties were:

```text
Driver:     local
Name:       opsforge-postgres-data
Mountpoint: /var/lib/docker/volumes/opsforge-postgres-data/_data
Scope:      local
```

The volume creation time was recorded as:

```text
2026-09-19T13:26:14Z
```

---

# Docker Desktop Storage Note

The reported mountpoint was:

```text
/var/lib/docker/volumes/opsforge-postgres-data/_data
```

On Docker Desktop for macOS, this location belongs to Docker's Linux runtime
environment.

It should not be treated as an ordinary Mac application directory that the
project manually manages.

The intended management interface is Docker:

```text
docker volume create
docker volume inspect
docker volume ls
docker volume rm
```

---

# Named Volume Mental Model

The desired architecture is:

```text
PostgreSQL container
        │
        ▼
/var/lib/postgresql/data
        │
        ▼
opsforge-postgres-data
```

The container can be deleted while:

```text
opsforge-postgres-data
```

remains independently managed.

Conceptually:

```text
Postgres container A
        │
        ▼
opsforge-postgres-data
        ▲
        │
Postgres container B
```

This separates:

```text
compute identity
```

from:

```text
data identity
```

---

# Starting PostgreSQL with Persistent Storage

PostgreSQL 16 was started using:

```bash
docker run -d \
  --name opsforge-postgres \
  --network opsforge-net \
  -e POSTGRES_DB=opsforge \
  -e POSTGRES_USER=opsforge \
  -e POSTGRES_PASSWORD=opsforge-local-dev \
  -v opsforge-postgres-data:/var/lib/postgresql/data \
  postgres:16
```

The important storage configuration was:

```text
opsforge-postgres-data:/var/lib/postgresql/data
```

The left side:

```text
opsforge-postgres-data
```

is the Docker-managed named volume.

The right side:

```text
/var/lib/postgresql/data
```

is the PostgreSQL data directory inside the container.

---

# PostgreSQL Was Kept Internal

The running container showed:

```text
5432/tcp
```

but no mapping such as:

```text
0.0.0.0:5432->5432/tcp
```

Therefore PostgreSQL was not published to the host.

The intended runtime model remained:

```text
application containers
        ↓
opsforge-net
        ↓
PostgreSQL :5432
```

rather than:

```text
host
 ↓
published PostgreSQL port
```

This continued the internal-service principle established with inventory.

---

# PostgreSQL Startup Evidence

The PostgreSQL logs showed successful initialization.

Important log messages included:

```text
starting PostgreSQL 16.14
```

and:

```text
listening on IPv4 address "0.0.0.0", port 5432
```

and:

```text
listening on IPv6 address "::", port 5432
```

and finally:

```text
database system is ready to accept connections
```

The initialization sequence also showed:

```text
CREATE DATABASE
```

followed by:

```text
PostgreSQL init process complete; ready for start up.
```

---

# PostgreSQL Readiness Verification

Instead of relying only on process existence or elapsed time, PostgreSQL
readiness was checked using:

```bash
docker exec opsforge-postgres \
  pg_isready \
  -U opsforge \
  -d opsforge
```

Result:

```text
/var/run/postgresql:5432 - accepting connections
```

This distinction is important:

```text
container running
        ≠
database ready
```

`pg_isready` verifies application-level readiness.

This concept will become important again during Docker Compose health checks.

---

# Creating the Persistence Probe

A dedicated test table was created:

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "CREATE TABLE IF NOT EXISTS a2_persistence_probe (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL
      );"
```

PostgreSQL returned:

```text
CREATE TABLE
```

A test row was inserted:

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "INSERT INTO a2_persistence_probe (message)
      VALUES ('A2.4 named volume survived container replacement');"
```

Result:

```text
INSERT 0 1
```

---

# Verifying Initial Persistent Data

The persistence table was queried:

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM a2_persistence_probe;"
```

Result:

```text
 id |                     message
----+--------------------------------------------------
  1 | A2.4 named volume survived container replacement
(1 row)
```

At this point:

```text
PostgreSQL process
        ↓
PostgreSQL data directory
        ↓
named volume
        ↓
a2_persistence_probe
        ↓
row 1
```

---

# Inspecting the PostgreSQL Mount

The container mounts were inspected:

```bash
docker inspect opsforge-postgres \
  --format '{{json .Mounts}}'
```

Docker reported:

```text
Type:        volume
Name:        opsforge-postgres-data
Source:      /var/lib/docker/volumes/opsforge-postgres-data/_data
Destination: /var/lib/postgresql/data
Driver:      local
RW:          true
```

This verified the intended mapping:

```text
opsforge-postgres-data
        │
        ▼
/var/lib/postgresql/data
```

---

# Main Persistence Experiment — Delete the PostgreSQL Container

The PostgreSQL container was completely removed:

```bash
docker rm -f opsforge-postgres
```

Docker returned:

```text
opsforge-postgres
```

A subsequent:

```bash
docker ps
```

showed only gateway and inventory.

The PostgreSQL container object no longer existed.

---

# Small Docker Filter Syntax Failure

The first attempt to confirm removal used:

```bash
docker ps -a --filter name-opsforge-postgres
```

Docker returned:

```text
invalid argument "name-opsforge-postgres" for "-f, --filter" flag:
bad format of filter (expected name=value)
```

The correct filter syntax was:

```bash
docker ps -a --filter name=opsforge-postgres
```

This returned no matching container.

The lesson was:

```text
Docker filter syntax
KEY=value
```

not:

```text
KEY-value
```

This was a command-line syntax issue, not a persistence failure.

---

# Verifying the Named Volume Survived Container Deletion

After deleting PostgreSQL:

```bash
docker volume ls | grep opsforge-postgres-data
```

returned:

```text
local     opsforge-postgres-data
```

Therefore:

```text
PostgreSQL container
        ❌ removed

opsforge-postgres-data
        ✅ still exists
```

This was the first critical persistence result.

Deleting compute did not delete the explicitly managed named volume.

---

# Recreating PostgreSQL with the Same Named Volume

A new PostgreSQL container was created using the same configuration:

```bash
docker run -d \
  --name opsforge-postgres \
  --network opsforge-net \
  -e POSTGRES_DB=opsforge \
  -e POSTGRES_USER=opsforge \
  -e POSTGRES_PASSWORD=opsforge-local-dev \
  -v opsforge-postgres-data:/var/lib/postgresql/data \
  postgres:16
```

A new container ID was returned:

```text
4a3020e26b83245d1e4424a819735017f76dce16fa39e49d5c3ffe536d583694
```

This was a different container from the original.

The storage identity remained:

```text
opsforge-postgres-data
```

---

# Readiness After Recreation

The new container was checked with:

```bash
docker exec opsforge-postgres \
  pg_isready \
  -U opsforge \
  -d opsforge
```

Result:

```text
/var/run/postgresql:5432 - accepting connections
```

The recreated PostgreSQL service was healthy.

---

# Persistence Proof After Container Replacement

The original table was queried:

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM a2_persistence_probe;"
```

Result:

```text
 id |                     message
----+--------------------------------------------------
  1 | A2.4 named volume survived container replacement
(1 row)
```

This proved the central A2.4 claim:

```text
original PostgreSQL container
        ↓
deleted

named volume
        ↓
survived

new PostgreSQL container
        ↓
attached same volume

original database state
        ↓
still available
```

---

# Persistence Architecture

Before replacement:

```text
┌──────────────────────────┐
│ PostgreSQL container A   │
│                          │
│ postgres process         │
└────────────┬─────────────┘
             │
             ▼
   opsforge-postgres-data
             │
             ▼
a2_persistence_probe
             │
             ▼
row 1
```

Container A was deleted:

```text
PostgreSQL container A
        ❌
```

The volume remained:

```text
opsforge-postgres-data
        ✅
```

After recreation:

```text
┌──────────────────────────┐
│ PostgreSQL container B   │
│                          │
│ new postgres process     │
└────────────┬─────────────┘
             │
             ▼
   opsforge-postgres-data
             │
             ▼
a2_persistence_probe
             │
             ▼
same row 1
```

This is persistent storage.

---

# Experiment — PostgreSQL Without Explicit Named Volume

A control experiment created another PostgreSQL container:

```bash
docker run -d \
  --name opsforge-postgres-ephemeral \
  --network opsforge-net \
  -e POSTGRES_DB=opsforge \
  -e POSTGRES_USER=opsforge \
  -e POSTGRES_PASSWORD=opsforge-local-dev \
  postgres:16
```

No explicit:

```text
-v opsforge-postgres-data:...
```

was provided.

The container was healthy:

```bash
docker exec opsforge-postgres-ephemeral \
  pg_isready \
  -U opsforge \
  -d opsforge
```

Result:

```text
/var/run/postgresql:5432 - accepting connections
```

---

# Creating Ephemeral-Control Data

A separate table was created:

```bash
docker exec opsforge-postgres-ephemeral \
  psql \
  -U opsforge \
  -d opsforge \
  -c "CREATE TABLE ephemeral_probe (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL
      );"
```

Result:

```text
CREATE TABLE
```

A row was inserted:

```bash
docker exec opsforge-postgres-ephemeral \
  psql \
  -U opsforge \
  -d opsforge \
  -c "INSERT INTO ephemeral_probe (message)
      VALUES ('this state belongs to this container');"
```

Result:

```text
INSERT 0 1
```

The row was confirmed:

```bash
docker exec opsforge-postgres-ephemeral \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM ephemeral_probe;"
```

Result:

```text
 id |               message
----+--------------------------------------
  1 | this state belongs to this container
(1 row)
```

---

# Delete and Recreate the Ephemeral-Control PostgreSQL

The container was removed:

```bash
docker rm -f opsforge-postgres-ephemeral
```

A new container with the same name was started:

```bash
docker run -d \
  --name opsforge-postgres-ephemeral \
  --network opsforge-net \
  -e POSTGRES_DB=opsforge \
  -e POSTGRES_USER=opsforge \
  -e POSTGRES_PASSWORD=opsforge-local-dev \
  postgres:16
```

The new container ID was different from the previous one.

The previous table was queried:

```bash
docker exec opsforge-postgres-ephemeral \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM ephemeral_probe;"
```

PostgreSQL returned:

```text
ERROR:  relation "ephemeral_probe" does not exist
LINE 1: SELECT * FROM ephemeral_probe;
                      ^
```

The previously created database object was no longer available through the
newly created container.

---

# Important PostgreSQL Image Storage Nuance

The PostgreSQL image has its own declared volume behavior.

The later Docker volume listing showed automatically generated volume names
such as:

```text
7cf9ccfbe78568187e817beaed3e5f1414945e55d13bfed31c3bc72a772e95f4
69d4fef32b8f2af12e5fe547237e5dc70f0624ade1e7a7978c71df2a6d6c6080
```

These are consistent with Docker-managed anonymous volumes created during
container usage.

Therefore the precise lesson is not simply:

```text
no -v
=
data always stored only in container writable layer
```

The stronger and more useful OpsForge lesson is:

> If persistent storage is not explicitly named and deliberately reattached,
> the project does not have a clear and reproducible storage identity.

The explicitly managed volume:

```text
opsforge-postgres-data
```

provides a predictable persistence contract.

The automatically generated volumes do not provide the same clear project-level
identity.

---

# Named Volume Versus Anonymous Volume

## Explicit Named Volume

```text
opsforge-postgres-data
```

Advantages:

```text
human-readable identity
easy inspection
intentional lifecycle
easy reattachment
clear infrastructure documentation
predictable Compose configuration
```

---

## Automatically Generated Volume

Example runtime identities observed:

```text
7cf9ccfbe785...
69d4fef32b8...
```

These may persist independently, but their relationship to application intent
is less obvious.

OpsForge therefore prefers explicitly named storage.

---

# Stop/Start Persistence Experiment

The real PostgreSQL container was stopped:

```bash
docker stop opsforge-postgres
```

and restarted:

```bash
docker start opsforge-postgres
```

Readiness was checked again:

```bash
docker exec opsforge-postgres \
  pg_isready \
  -U opsforge \
  -d opsforge
```

Result:

```text
/var/run/postgresql:5432 - accepting connections
```

The persistence table was queried again:

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM a2_persistence_probe;"
```

Result:

```text
 id |                     message
----+--------------------------------------------------
  1 | A2.4 named volume survived container replacement
(1 row)
```

This confirmed persistence across:

```text
stop
 ↓
start
```

as expected.

---

# Why Delete/Recreate Was the Stronger Experiment

Stop/start alone proves:

```text
same container
      ↓
same attached storage
      ↓
data remains
```

Delete/recreate proves something stronger:

```text
old container removed completely
        ↓
new container created
        ↓
same external storage attached
        ↓
data remains
```

Therefore A2.4's main persistence claim rests on the delete/recreate experiment,
not only the stop/start test.

---

# Inspecting PostgreSQL Storage Identity

The simplified mount inspection:

```bash
docker inspect opsforge-postgres \
  --format '{{range .Mounts}}{{println .Type .Name .Destination}}{{end}}'
```

returned:

```text
volume opsforge-postgres-data /var/lib/postgresql/data
```

This concisely proves:

```text
storage type:
volume

storage identity:
opsforge-postgres-data

container mount path:
/var/lib/postgresql/data
```

---

# PostgreSQL Network Identity

The PostgreSQL container network configuration was inspected:

```bash
docker inspect opsforge-postgres \
  --format '{{json .NetworkSettings.Networks}}'
```

The container was attached to:

```text
opsforge-net
```

with:

```text
Gateway:
172.20.0.1

IPAddress:
172.20.0.4

DNSNames:
opsforge-postgres
4a3020e26b83
```

This gave PostgreSQL a separate network identity from its storage identity.

---

# Full OpsForge Bridge State During A2.4

The Docker bridge was inspected:

```bash
docker network inspect opsforge-net
```

Important network properties remained:

```text
Name:       opsforge-net
Driver:     bridge
Subnet:     172.20.0.0/16
Gateway:    172.20.0.1
IPv6:       disabled
```

At the time of inspection, the network contained:

```text
opsforge-inventory
    172.20.0.2

opsforge-gateway
    172.20.0.3

opsforge-postgres
    172.20.0.4

opsforge-postgres-ephemeral
    172.20.0.5
```

The ephemeral database was later removed.

---

# Combining Network and Storage Isolation

PostgreSQL now had two independent runtime relationships.

## Network

```text
opsforge-postgres
        ↓
opsforge-net
        ↓
172.20.0.4
```

## Storage

```text
opsforge-postgres
        ↓
/var/lib/postgresql/data
        ↓
opsforge-postgres-data
```

Therefore the PostgreSQL container participates simultaneously in:

```text
network isolation
```

and:

```text
persistent external storage
```

---

# DNS Resolution for PostgreSQL

The gateway tested PostgreSQL service discovery:

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-postgres'))"
```

Result:

```text
172.20.0.4
```

This demonstrated:

```text
gateway
   ↓
Docker DNS
   ↓
opsforge-postgres
   ↓
172.20.0.4
```

The gateway could resolve the database container by logical service identity.

This reused the A2.3 Docker DNS model.

---

# Network Identity Versus Storage Identity

The experiment now exposes three different identities.

## Process Identity

Inside PostgreSQL there is a running process with its own PID namespace.

## Network Identity

```text
opsforge-postgres
172.20.0.4
```

## Storage Identity

```text
opsforge-postgres-data
```

These are not the same thing.

Conceptually:

```text
PROCESS
   │
   ├── runtime PID
   │
   ▼
CONTAINER
   │
   ├── network identity
   │      opsforge-postgres
   │
   └── storage attachment
          opsforge-postgres-data
```

Deleting a container can change:

```text
process identity
container identity
network endpoint identity
```

while leaving:

```text
named volume identity
```

unchanged.

---

# Container Identity Versus Data Identity

The first PostgreSQL container had one container ID.

After deletion and recreation, PostgreSQL received a new container ID:

```text
4a3020e26b83245d1e4424a819735017f76dce16fa39e49d5c3ffe536d583694
```

However both runtime instances used:

```text
opsforge-postgres-data
```

Therefore:

```text
container identity
        ≠
data identity
```

This is a core cloud-native storage principle.

---

# Stateless Application Services Versus Durable State

A2.4 also clarifies how different OpsForge components should treat state.

## Gateway

Gateway is intended to be replaceable compute.

Important durable state should not live in its container filesystem.

## Inventory

Inventory is also currently treated as replaceable application compute.

## Worker

The worker should be replaceable compute.

Work coordination belongs in external systems such as Redis and PostgreSQL.

## PostgreSQL

PostgreSQL is the durable system-of-record component.

Its data requires explicit persistent storage.

## Redis

Redis serves the queue/coordination role in Track A.

Its durability requirements differ from PostgreSQL and will be handled
intentionally rather than assuming all state has identical persistence needs.

---

# Stateless Does Not Mean No State Exists

Calling gateway stateless does not mean the overall application has no state.

It means gateway does not own durable application state in its local
container filesystem.

Conceptually:

```text
gateway
   │
   │ compute
   ▼
PostgreSQL
   │
   ▼
durable order state
```

This allows gateway containers to be replaced independently of durable data.

---

# Storage Ownership Decision

A2.4 establishes a useful default decision model.

```text
container writable layer
    → temporary runtime files

bind mount
    → host-managed development/configuration files

named volume
    → Docker-managed persistent application state
```

For OpsForge PostgreSQL:

```text
named volume
```

is the intended local development persistence mechanism.

---

# Bind Mount Versus Named Volume

## Bind Mount

```text
Host owns exact filesystem path
        ↓
Container sees that path
```

Example used:

```text
/tmp/opsforge-bind-demo
        ↓
/data
```

Useful when host visibility and host editing are intentional.

---

## Named Volume

```text
Docker owns persistent storage
        ↓
Container mounts storage
```

Example:

```text
opsforge-postgres-data
        ↓
/var/lib/postgresql/data
```

Useful when application data must outlive a particular container without tying
the project to a manually selected host directory.

---

# Mount Paths Can Hide Existing Image Content

A mounted path replaces the container's visible view at that location.

Conceptually:

```text
image contains:

/some/path/file.txt
```

then runtime mounts:

```text
volume → /some/path
```

The mounted data becomes visible at:

```text
/some/path
```

and can obscure files originally provided by the image at that location.

Therefore mount destinations must be selected deliberately.

For PostgreSQL, the official data directory is intentionally used as the
volume destination.

---

# Explicit Persistence Contract

The A2.4 storage contract for PostgreSQL is now:

```text
service:
opsforge-postgres

database:
opsforge

volume:
opsforge-postgres-data

mount:
opsforge-postgres-data
        ↓
/var/lib/postgresql/data

network:
opsforge-net

service identity:
opsforge-postgres
```

This is considerably clearer than depending on automatically generated runtime
storage.

---

# Storage Lifecycle

The named-volume lifecycle can now be described as:

```text
docker volume create
        ↓
volume exists

docker run -v volume:/path
        ↓
container uses volume

docker rm container
        ↓
container disappears

volume
        ↓
still exists

new container mounts same volume
        ↓
old data available

docker volume rm volume
        ↓
persistent data intentionally destroyed
```

Storage destruction is therefore a separate lifecycle action from container
destruction.

---

# Important Destructive Operations

The persistent volume should not be removed casually.

A command such as:

```bash
docker volume rm opsforge-postgres-data
```

would intentionally remove the managed PostgreSQL storage.

Similarly, broad cleanup operations involving volumes can destroy persistent
state.

Therefore OpsForge teardown semantics must eventually distinguish between:

```text
stop/remove compute
```

and:

```text
destroy persistent state
```

This distinction will matter when the project gains canonical Compose and
Makefile lifecycle commands.

---

# Local Runtime Cleanup Semantics

A future local command such as:

```text
make local-down
```

should not automatically be assumed to mean:

```text
delete all persistent data
```

A separate stronger cleanup action may eventually be responsible for removing
named volumes.

The project should make that behavior explicit.

This prevents accidental state destruction.

---

# Failure-Diagnosis Model for Persistent Storage

If expected PostgreSQL data disappears, the diagnostic process should be
layered.

```text
1. Is the expected PostgreSQL container running?

2. Which named volume is mounted?

3. What destination path is mounted?

4. Is PostgreSQL actually using that destination?

5. Was the new container recreated with the same volume?

6. Does the named volume still exist?

7. Is the client connected to the expected database?

8. Does the expected schema/table exist?

9. Was the named volume itself intentionally or accidentally deleted?
```

Useful diagnostics include:

```bash
docker ps -a
```

```bash
docker volume ls
```

```bash
docker volume inspect opsforge-postgres-data
```

```bash
docker inspect opsforge-postgres \
  --format '{{range .Mounts}}{{println .Type .Name .Destination}}{{end}}'
```

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c '\dt'
```

The goal is to diagnose using evidence rather than assuming Docker deleted the
data.

---

# Relationship to Readiness

PostgreSQL also demonstrated the difference between lifecycle and readiness.

A running container means:

```text
container process exists
```

while:

```bash
pg_isready
```

tests whether PostgreSQL can actually accept database connections.

Therefore:

```text
container started
        ≠
database ready
```

This is an important transition toward the upcoming Docker Compose readiness
work.

---

# Relationship to Kubernetes

The A2.4 mental model prepares directly for Kubernetes persistent storage.

Docker:

```text
container
   ↓
named volume
```

later evolves conceptually toward:

```text
Pod
 ↓
PersistentVolumeClaim
 ↓
PersistentVolume
```

The underlying principle is the same:

```text
compute is replaceable
        ↓
storage has an independent lifecycle
```

A Pod or container should not automatically be treated as the durable owner of
important application data.

---

# Final A2.4 Runtime Architecture

At the end of the persistence experiments, the meaningful OpsForge local
topology was:

```text
                         macOS HOST

                             │
                             │ published port
                             ▼

                    opsforge-gateway
                       172.20.0.3
                          :8000
                             │
                             │
                  ┌──────────┴───────────┐
                  │                      │
                  ▼                      ▼

       opsforge-inventory        opsforge-postgres
          172.20.0.2                172.20.0.4
             :8001                     :5432
                                          │
                                          │ volume mount
                                          ▼
                              opsforge-postgres-data
                                          │
                                          ▼
                              /var/lib/postgresql/data
```

All application containers were attached to:

```text
opsforge-net
```

using subnet:

```text
172.20.0.0/16
```

with bridge gateway:

```text
172.20.0.1
```

The temporary ephemeral PostgreSQL test container was removed at the end.

---

# Cleanup Performed

The temporary comparison database was removed:

```bash
docker rm -f opsforge-postgres-ephemeral \
  2>/dev/null || true
```

Docker returned:

```text
opsforge-postgres-ephemeral
```

The temporary bind-mount demonstration directory was removed:

```bash
rm -rf /tmp/opsforge-bind-demo
```

The real PostgreSQL service and named volume remained available for continued
OpsForge work.

---

# Reproducible A2.4 Commands

## Bind Mount Demo

```bash
rm -rf /tmp/opsforge-bind-demo
mkdir -p /tmp/opsforge-bind-demo

echo "created on the Mac Host" \
  > /tmp/opsforge-bind-demo/host.txt

cat /tmp/opsforge-bind-demo/host.txt
```

```bash
docker run --rm \
  -v /tmp/opsforge-bind-demo:/data \
  alpine:3.22 \
  sh -c 'ls -la /data && cat /data/host.txt'
```

```bash
docker run --rm \
  -v /tmp/opsforge-bind-demo:/data \
  alpine:3.22 \
  sh -c 'echo "created by container" > /data/container.txt'
```

```bash
cat /tmp/opsforge-bind-demo/container.txt
```

---

## Create Named Volume

```bash
docker volume create opsforge-postgres-data
```

```bash
docker volume inspect opsforge-postgres-data
```

---

## Start Persistent PostgreSQL

```bash
docker run -d \
  --name opsforge-postgres \
  --network opsforge-net \
  -e POSTGRES_DB=opsforge \
  -e POSTGRES_USER=opsforge \
  -e POSTGRES_PASSWORD=opsforge-local-dev \
  -v opsforge-postgres-data:/var/lib/postgresql/data \
  postgres:16
```

---

## Check Readiness

```bash
docker exec opsforge-postgres \
  pg_isready \
  -U opsforge \
  -d opsforge
```

---

## Create Persistence Probe

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "CREATE TABLE IF NOT EXISTS a2_persistence_probe (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL
      );"
```

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "INSERT INTO a2_persistence_probe (message)
      VALUES ('A2.4 named volume survived container replacement');"
```

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM a2_persistence_probe;"
```

---

## Inspect Mount

```bash
docker inspect opsforge-postgres \
  --format '{{json .Mounts}}'
```

---

## Delete Container

```bash
docker rm -f opsforge-postgres
```

Verify it is gone:

```bash
docker ps -a \
  --filter name=opsforge-postgres
```

Verify volume remains:

```bash
docker volume ls \
  | grep opsforge-postgres-data
```

---

## Recreate Using Same Volume

```bash
docker run -d \
  --name opsforge-postgres \
  --network opsforge-net \
  -e POSTGRES_DB=opsforge \
  -e POSTGRES_USER=opsforge \
  -e POSTGRES_PASSWORD=opsforge-local-dev \
  -v opsforge-postgres-data:/var/lib/postgresql/data \
  postgres:16
```

---

## Verify Persistence

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM a2_persistence_probe;"
```

Expected:

```text
A2.4 named volume survived container replacement
```

---

## Stop/Start Test

```bash
docker stop opsforge-postgres
docker start opsforge-postgres
```

```bash
docker exec opsforge-postgres \
  pg_isready \
  -U opsforge \
  -d opsforge
```

```bash
docker exec opsforge-postgres \
  psql \
  -U opsforge \
  -d opsforge \
  -c "SELECT * FROM a2_persistence_probe;"
```

---

## Inspect Simplified Mount Mapping

```bash
docker inspect opsforge-postgres \
  --format '{{range .Mounts}}{{println .Type .Name .Destination}}{{end}}'
```

Expected:

```text
volume opsforge-postgres-data /var/lib/postgresql/data
```

---

## Inspect Network Attachment

```bash
docker inspect opsforge-postgres \
  --format '{{json .NetworkSettings.Networks}}'
```

---

## Resolve PostgreSQL Through Docker DNS

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-postgres'))"
```

Observed:

```text
172.20.0.4
```

---

# A2.4 Evidence Summary

| Experiment                                                          | Observed Result |
| ------------------------------------------------------------------- | --------------- |
| Host bind-mount directory created                                   | ✅               |
| Host file visible inside Alpine container                           | ✅               |
| Container-created file visible on Mac host                          | ✅               |
| Temporary Alpine containers removed automatically                   | ✅               |
| Bind-mounted host files remained after container exit               | ✅               |
| `opsforge-postgres-data` named volume created                       | ✅               |
| Volume uses Docker `local` driver                                   | ✅               |
| PostgreSQL 16 container started on `opsforge-net`                   | ✅               |
| PostgreSQL remained internal with `5432/tcp` only                   | ✅               |
| PostgreSQL reported ready to accept connections                     | ✅               |
| `pg_isready` confirmed readiness                                    | ✅               |
| `a2_persistence_probe` table created                                | ✅               |
| Persistence probe row inserted                                      | ✅               |
| Named volume mounted at `/var/lib/postgresql/data`                  | ✅               |
| PostgreSQL container deleted completely                             | ✅               |
| Named volume remained after container deletion                      | ✅               |
| New PostgreSQL container created with same named volume             | ✅               |
| Original persistence row survived replacement                       | ✅               |
| PostgreSQL without explicit named volume created test state         | ✅               |
| Test container deleted and recreated                                | ✅               |
| `ephemeral_probe` relation no longer existed in recreated container | ✅               |
| Anonymous/runtime-generated volume identities observed              | ✅               |
| Real PostgreSQL survived stop/start                                 | ✅               |
| Named persistence row survived stop/start                           | ✅               |
| Simplified mount inspection confirmed named volume                  | ✅               |
| PostgreSQL attached to `opsforge-net`                               | ✅               |
| PostgreSQL received `172.20.0.4`                                    | ✅               |
| Gateway resolved `opsforge-postgres` through Docker DNS             | ✅               |
| Temporary ephemeral PostgreSQL removed                              | ✅               |
| Temporary bind-mount directory removed                              | ✅               |

---

# Key Lessons

## 1. Container Lifecycle and Data Lifecycle Are Separate

```text
delete container
        ≠
delete named volume
```

when storage is managed explicitly.

---

## 2. Stop and Remove Are Different

```text
stop
=
process stops but container remains

remove
=
container object is deleted
```

Delete/recreate is the stronger persistence test.

---

## 3. Bind Mounts Are Host-Managed

The host directory remains authoritative.

```text
host path
    ↕
container path
```

Changes can be observed from both sides.

---

## 4. Named Volumes Are Docker-Managed

```text
opsforge-postgres-data
```

provides a stable storage identity independent of a particular PostgreSQL
container.

---

## 5. PostgreSQL Is Durable State

PostgreSQL owns data that must survive compute replacement.

Its storage therefore requires an explicit persistence mechanism.

---

## 6. Gateway and Inventory Should Remain Disposable

Application compute should not depend on local container filesystem state for
important durable information.

---

## 7. Explicit Storage Identity Is Better Than Accidental Runtime Storage

A named volume such as:

```text
opsforge-postgres-data
```

is easier to understand, document, reattach, inspect, and later reproduce in
Compose than runtime-generated anonymous volume identifiers.

---

## 8. Network Identity and Storage Identity Are Different

PostgreSQL had:

```text
network identity:
opsforge-postgres
172.20.0.4
```

and:

```text
storage identity:
opsforge-postgres-data
```

These lifecycles are independent.

---

## 9. Readiness Is Different from Running

```text
docker ps says Up
```

does not prove PostgreSQL can accept connections.

```text
pg_isready
```

provided the application-level readiness check.

---

## 10. Delete/Recreate Proved Real Persistence

The central experiment was:

```text
insert row
    ↓
delete PostgreSQL container
    ↓
confirm volume remains
    ↓
create new PostgreSQL container
    ↓
attach same named volume
    ↓
query original row successfully
```

This is the strongest evidence produced in A2.4.

---

# A2.4 Learning Outcome

A2.4 established that containers and persistent state should be treated as
separate architectural concerns.

The central storage relationship is:

```text
APPLICATION COMPUTE
        ↓
container
        ↓
replaceable


DURABLE STATE
        ↓
named volume
        ↓
independent lifecycle
```

For PostgreSQL:

```text
PostgreSQL container
        ↓
/var/lib/postgresql/data
        ↓
opsforge-postgres-data
```

The PostgreSQL container was deleted and recreated, while the persistence probe
row survived.

This proved:

```text
compute replacement
        ≠
state destruction
```

when storage is designed correctly.

---

# Mental Model After A2.4

The OpsForge local architecture has now evolved through four major container
concepts:

```text
A2.1
Image → Container → PID 1


A2.2
Host → Published Port → Container


A2.3
Container → Docker DNS → Container


A2.4
Container → Named Volume → Persistent State
```

Together:

```text
                         HOST
                           │
                           ▼
                  published gateway
                           │
                           ▼
                 opsforge-gateway
                           │
                Docker DNS / bridge
                 ┌─────────┴─────────┐
                 ▼                   ▼
       opsforge-inventory    opsforge-postgres
                                      │
                                      ▼
                           /var/lib/postgresql/data
                                      │
                                      ▼
                           opsforge-postgres-data
```

We now understand:

```text
process lifecycle
container lifecycle
network lifecycle
storage lifecycle
```

as separate but cooperating concerns.

---

# Transition to A2.5

A2.4 solved:

> How can durable application state survive container replacement?

The next problem is:

> How should our application images be built efficiently and safely for a
> production-oriented runtime?

A2.5 therefore moves into:

```text
Docker image layers
build cache behavior
cold versus cached builds
multi-stage builds
image size
minimal runtime images
dependency boundaries
```

The existing gateway and inventory Dockerfiles are intentionally still simple.

The next step is to measure them before optimizing them, then build improved
versions and compare the results.

The principle remains:

```text
measure first
        ↓
change architecture
        ↓
measure again
        ↓
explain the difference
```

