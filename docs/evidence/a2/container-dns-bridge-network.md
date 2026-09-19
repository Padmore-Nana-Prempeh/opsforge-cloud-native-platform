# A2.3 — Docker Bridge Networks, Container DNS, and Service-to-Service Communication

## Objective

Understand how containerized OpsForge services communicate with one another
without relying on host loopback addresses or hardcoded container IP
addresses.

This subsection extends the networking model established in A2.2.

A2.2 answered:

> How does the host reach an application running inside a container?

A2.3 answers:

> How does one container reach another container?

The experiments focus on:

* user-defined Docker bridge networks,
* container network namespaces,
* service-to-service communication,
* Docker DNS,
* container names as service identities,
* internal versus published ports,
* runtime configuration through environment variables,
* why `127.0.0.1` changes meaning inside containers,
* DNS failure diagnosis,
* service recovery,
* and why application code should not depend on ephemeral container IPs.

---

# Starting Point

At the beginning of A2.3, the gateway had already been containerized.

The gateway image available locally included:

```text
opsforge-gateway:a2.1
opsforge-gateway:a2.2
```

A2.2 had already demonstrated that the gateway could be reached from the host
through explicit port publishing.

For example:

```text
127.0.0.1:8020 -> container :8000
```

and:

```bash
curl http://127.0.0.1:8020/health/live
```

returned:

```json
{"status":"alive"}
```

The gateway logs confirmed:

```text
Uvicorn running on http://0.0.0.0:8000
```

This established the host-to-container path.

A2.3 introduces the second application container:

```text
inventory-api
```

and moves from:

```text
host → container
```

to:

```text
container → container
```

---

# Networking Model from A1

During A1, both gateway and inventory ran as ordinary processes on the same
host.

The architecture was:

```text
macOS host
│
├── gateway-api
│      127.0.0.1:8000
│
└── inventory-api
       127.0.0.1:8001
```

Because both processes shared the host network namespace, gateway could call:

```text
http://127.0.0.1:8001
```

and reach inventory.

The mental model was:

```text
ONE HOST
ONE NETWORK STACK
ONE LOOPBACK INTERFACE

127.0.0.1
│
├── gateway :8000
└── inventory :8001
```

Containerization breaks this assumption.

---

# Container Network Namespace Model

Once gateway and inventory exist in separate containers, each container has
its own network namespace.

Conceptually:

```text
┌──────────────────────────┐
│ gateway container        │
│                          │
│ 127.0.0.1                │
│     │                    │
│     └── gateway :8000    │
└──────────────────────────┘


┌──────────────────────────┐
│ inventory container      │
│                          │
│ 127.0.0.1                │
│     │                    │
│     └── inventory :8001  │
└──────────────────────────┘
```

Therefore:

```text
127.0.0.1
```

does not mean:

```text
the entire Docker host
```

or:

```text
another container
```

It means:

> the loopback interface of the current network namespace.

Inside the gateway container:

```text
127.0.0.1
=
gateway container itself
```

Inside the inventory container:

```text
127.0.0.1
=
inventory container itself
```

This became one of the central lessons of A2.3.

---

# Containerizing Inventory

A Dockerfile was created:

```text
docker/inventory.Dockerfile
```

The initial design followed the same simple container baseline as gateway.

Conceptually:

```dockerfile
FROM python:3.13-slim

WORKDIR /opt/opsforge

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8001

CMD [
    "uvicorn",
    "app.inventory.main:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8001"
]
```

Inventory binds to:

```text
0.0.0.0:8001
```

so that it can receive traffic arriving through its Docker network interface.

---

# Inventory Build Failure and Diagnosis

The first inventory build was attempted using:

```bash
docker build \
  -f docker/inventory.Dockerfile \
  -t opsforge-inventory:a2.3 \
  .
```

The build failed at:

```dockerfile
COPY requirement.txt .
```

Docker reported:

```text
ERROR [3/5] COPY requirement.txt .
```

and:

```text
"/requirement.txt": not found
```

The repository file was actually:

```text
requirements.txt
```

with an `s`.

The Dockerfile also initially referenced:

```text
requirement.txt
```

during dependency installation.

The failure therefore occurred because the Docker build instruction referenced a
file that did not exist in the build context.

The diagnostic model was:

```text
Docker engine
    ✅ working

Dockerfile loaded
    ✅

build context loaded
    ✅

COPY source file
    ❌ incorrect filename
```

The Dockerfile was corrected to:

```dockerfile
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
```

---

# Successful Inventory Image Build

The image was rebuilt:

```bash
docker build \
  -f docker/inventory.Dockerfile \
  -t opsforge-inventory:a2.3 \
  .
```

The second build completed successfully.

Important build output included:

```text
CACHED [2/5] WORKDIR /opt/opsforge
CACHED [3/5] COPY requirements.txt .
CACHED [4/5] RUN pip install --no-cache-dir -r requirements.txt
CACHED [5/5] COPY app ./app
```

The image was created as:

```text
opsforge-inventory:a2.3
```

The local OpsForge images were:

```text
opsforge-gateway:a2.1
opsforge-gateway:a2.2
opsforge-inventory:a2.3
```

This also provided an early example of Docker build cache reuse.

After correcting the Dockerfile, unchanged layers did not need to be rebuilt.

---

# Inventory Import Verification

Before starting the service normally, the image's Python application import was
tested directly:

```bash
docker run --rm \
  opsforge-inventory:a2.3 \
  python -c "import app.inventory.main; print('inventory import ok')"
```

Result:

```text
inventory import ok
```

This verified that:

```text
image exists
    ↓
Python runtime works
    ↓
application source exists
    ↓
inventory module imports
```

before introducing networking.

This continues the layered troubleshooting discipline established in A2.1.

---

# Creating the User-Defined Docker Bridge Network

A dedicated Docker network was created:

```bash
docker network create opsforge-net
```

Docker returned network ID:

```text
17dc73e824881c353f0ba680a4bd2cf4f33c49900fee762fbc494b17d85474f9
```

The network was confirmed with:

```bash
docker network ls
```

which showed:

```text
opsforge-net    bridge    local
```

The complete local network list also included Docker's default networks and
other unrelated local development networks.

The important OpsForge network was:

```text
NAME           DRIVER
opsforge-net   bridge
```

---

# Inspecting the Bridge Network

The new network was inspected:

```bash
docker network inspect opsforge-net
```

Important properties included:

```text
Name:       opsforge-net
Driver:     bridge
EnableIPv4: true
EnableIPv6: false
Subnet:     172.20.0.0/16
Gateway:    172.20.0.1
```

Before any application containers were attached:

```text
Containers: {}
```

The network model was therefore:

```text
opsforge-net
│
├── driver: bridge
├── subnet: 172.20.0.0/16
├── gateway: 172.20.0.1
└── containers: none yet
```

---

# What the Docker Bridge Represents

The user-defined bridge acts conceptually like a virtual Layer-2 network
connecting container interfaces.

```text
                   opsforge-net

              Docker bridge network

        ┌──────────────┴───────────────┐
        │                              │
        ▼                              ▼

gateway container              inventory container
network interface              network interface
```

Each attached container receives:

* its own network namespace,
* its own loopback interface,
* an interface connected to the Docker bridge,
* an IP address on the bridge subnet,
* and access to Docker's embedded DNS behavior for connected container names.

---

# Starting Inventory as an Internal Service

Inventory was started using:

```bash
docker run -d \
  --name opsforge-inventory \
  --network opsforge-net \
  opsforge-inventory:a2.3
```

Important options were:

```text
-d
```

for detached mode,

```text
--name opsforge-inventory
```

for stable container identity, and:

```text
--network opsforge-net
```

to attach it to the OpsForge bridge.

No host port was published.

There was deliberately no:

```text
-p 8001:8001
```

---

# Internal Port Versus Published Port

`docker ps` showed:

```text
opsforge-inventory
PORTS: 8001/tcp
```

This meant the container used/exposed:

```text
8001/tcp
```

internally.

It did **not** mean:

```text
host :8001 -> container :8001
```

There was no host mapping such as:

```text
0.0.0.0:8001->8001/tcp
```

The intended architecture was:

```text
Mac
 │
 X
 │
inventory :8001


other container on opsforge-net
 │
 ▼
inventory :8001
```

Inventory became an internal application service rather than a host-published
entry point.

---

# Proving Inventory Was Not Reachable from the Host

The host attempted:

```bash
curl http://127.0.0.1:8001/inventory/widget-456
```

Result:

```text
curl: (7) Failed to connect to 127.0.0.1 port 8001
```

This was expected.

Inventory was running:

```text
✅
```

but its port was not published onto the host:

```text
❌
```

Therefore:

```text
container :8001
        ≠
host :8001
```

This reinforced the port-publishing lesson from A2.2.

---

# Inspecting Inventory Network Attachment

Inventory network configuration was inspected using:

```bash
docker inspect \
  opsforge-inventory \
  --format '{{json .NetworkSettings.Networks}}'
```

The result showed attachment to:

```text
opsforge-net
```

with:

```text
Gateway:   172.20.0.1
IPAddress: 172.20.0.2
```

Docker also reported DNS names including:

```text
opsforge-inventory
```

and the abbreviated container identity.

A simpler inspection returned:

```bash
docker inspect \
  opsforge-inventory \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

Result:

```text
172.20.0.2
```

At this moment the topology was:

```text
opsforge-net
172.20.0.0/16
│
├── gateway: 172.20.0.1
│
└── inventory: 172.20.0.2
```

The address was observed for learning and diagnostics.

It was not placed into application configuration.

---

# Why Hardcoded Container IPs Are Avoided

The inventory container happened to receive:

```text
172.20.0.2
```

But container IP addresses are runtime details.

Application code should not contain:

```text
http://172.20.0.2:8001
```

because lifecycle operations such as:

```text
delete
recreate
reschedule
network reconnect
```

may change runtime addresses.

The desired model is:

```text
stable service identity
        ↓
DNS resolution
        ↓
current container IP
```

instead of:

```text
application
        ↓
hardcoded ephemeral IP
```

---

# Verifying Docker DNS with a Temporary Container

A temporary Python container was attached to the same network:

```bash
docker run --rm \
  --network opsforge-net \
  python:3.13-slim \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventory'))"
```

The Python base image was not yet locally available, so Docker first pulled:

```text
python:3.13-slim
```

The DNS lookup returned:

```text
172.20.0.2
```

This matched the inventory address observed through:

```bash
docker inspect
```

The experiment proved:

```text
temporary container
        │
        │ query: opsforge-inventory
        ▼
Docker DNS
        │
        ▼
172.20.0.2
```

The container name became a resolvable service identity on the user-defined
bridge network.

---

# Verifying HTTP Communication Through Docker DNS

A second temporary-container test performed an actual HTTP request:

```bash
docker run --rm \
  --network opsforge-net \
  python:3.13-slim \
  python -c \
  "import urllib.request; print(urllib.request.urlopen('http://opsforge-inventory:8001/inventory/widget-456').read().decode())"
```

Result:

```json
{"item_id":"widget-456","available":true,"quantity":100}
```

This demonstrated a complete internal request:

```text
temporary container
        ↓
resolve opsforge-inventory
        ↓
Docker DNS
        ↓
172.20.0.2
        ↓
container port 8001
        ↓
Uvicorn
        ↓
inventory FastAPI route
        ↓
JSON response
```

The host still could not access `127.0.0.1:8001`, while another container on
the Docker network successfully accessed inventory.

Therefore:

```text
HOST ACCESS

Mac → inventory
❌


INTERNAL CONTAINER ACCESS

container → opsforge-inventory:8001
✅
```

---

# Starting Gateway on the Same Bridge Network

Gateway was then started on `opsforge-net`.

The first attempt failed because a previously created container still owned the
name:

```text
opsforge-gateway
```

Docker reported:

```text
Conflict. The container name "/opsforge-gateway" is already in use
```

This was not a networking failure.

It was a container lifecycle/name conflict.

The old container was stopped:

```bash
docker stop opsforge-gateway
```

and removed:

```bash
docker rm opsforge-gateway
```

The container name then became available again.

---

# Correct Gateway Runtime Configuration

Gateway was started with:

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://opsforge-inventory:8001 \
  opsforge-gateway:a2.2
```

This command defines three different connectivity concerns.

## 1. Internal Docker Network

```text
--network opsforge-net
```

allows:

```text
gateway
   ↕
inventory
```

through the shared bridge.

---

## 2. Host Entry Point

```text
-p 127.0.0.1:8000:8000
```

allows:

```text
Mac
 ↓
gateway
```

while limiting the published host interface to loopback.

---

## 3. Downstream Service Location

```text
-e INVENTORY_URL=http://opsforge-inventory:8001
```

configures gateway to use Docker DNS for inventory rather than host-style
loopback addressing.

---

# Resulting Architecture

The running architecture became:

```text
                         macOS HOST

curl
 │
 ▼
127.0.0.1:8000
 │
 │ Docker published port
 ▼


                    opsforge-net
                  172.20.0.0/16

┌─────────────────────────────┐
│ opsforge-gateway            │
│                             │
│ IP: 172.20.0.3              │
│ container port: 8000        │
│                             │
│ INVENTORY_URL=              │
│ http://opsforge-inventory:  │
│ 8001                        │
└──────────────┬──────────────┘
               │
               │ Docker DNS
               │ internal HTTP
               ▼
┌─────────────────────────────┐
│ opsforge-inventory          │
│                             │
│ IP: 172.20.0.2              │
│ container port: 8001        │
│ no host publication         │
└─────────────────────────────┘
```

---

# Verifying Both Containers on the Bridge

The network was inspected again:

```bash
docker network inspect opsforge-net
```

The output now contained both containers.

Gateway:

```text
Name:        opsforge-gateway
IPv4Address: 172.20.0.3/16
```

Inventory:

```text
Name:        opsforge-inventory
IPv4Address: 172.20.0.2/16
```

This confirmed:

```text
gateway
   │
   └── opsforge-net

inventory
   │
   └── opsforge-net
```

Both services shared the same user-defined bridge.

---

# DNS Resolution from the Actual Gateway Container

Docker DNS was tested from inside the real gateway container:

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventory'))"
```

Result:

```text
172.20.0.2
```

This proved:

```text
gateway container
       ↓
lookup "opsforge-inventory"
       ↓
Docker DNS
       ↓
172.20.0.2
```

No hardcoded address was required.

---

# Direct HTTP from Gateway to Inventory

A raw HTTP request was executed inside gateway:

```bash
docker exec opsforge-gateway \
  python -c \
  "import urllib.request; print(urllib.request.urlopen('http://opsforge-inventory:8001/inventory/widget-456').read().decode())"
```

Result:

```json
{"item_id":"widget-456","available":true,"quantity":100}
```

This isolated the underlying container networking behavior from the gateway's
business logic.

It proved:

```text
gateway process environment
        ↓
DNS resolution
        ↓
Docker bridge
        ↓
inventory network interface
        ↓
port 8001
        ↓
HTTP
        ↓
inventory response
```

---

# Full End-to-End Request Through Gateway

The host then called:

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

Result:

```text
HTTP/1.1 200 OK
```

with:

```json
{
  "gateway": "ok",
  "inventory": {
    "item_id": "widget-456",
    "available": true,
    "quantity": 100
  }
}
```

This proved the complete path:

```text
Mac curl
    ↓
host 127.0.0.1:8000
    ↓
Docker published port
    ↓
gateway :8000
    ↓
INVENTORY_URL
    ↓
Docker DNS
    ↓
opsforge-inventory
    ↓
inventory :8001
    ↓
inventory response
    ↓
gateway response
    ↓
Mac
```

This was the first complete OpsForge container-to-container application flow.

---

# Failure Experiment — Incorrect `docker run` Environment Syntax

During the localhost experiment, the following malformed syntax was attempted:

```bash
-e INVENTORY_URL = http://127.0.01:8001
```

Docker returned:

```text
invalid reference format
```

The problem was not the application.

The command-line syntax incorrectly placed spaces around:

```text
=
```

for the environment assignment.

The correct syntax is:

```bash
-e INVENTORY_URL=http://127.0.0.1:8001
```

This provides another troubleshooting distinction:

```text
Docker CLI parsing failure
        ≠
container network failure
        ≠
application failure
```

The malformed command failed before a new container was successfully started.

---

# Failure Experiment — Using 127.0.0.1 for Inventory

Gateway was deliberately restarted using the old A1 inventory location:

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://127.0.0.1:8001 \
  opsforge-gateway:a2.2
```

The host called:

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

The gateway returned:

```text
HTTP/1.1 503 Service Unavailable
```

with:

```json
{"detail":"Inventory service unavailable"}
```

Inventory itself was still running.

The failure occurred because gateway interpreted:

```text
127.0.0.1
```

as its own loopback interface.

The actual lookup path was:

```text
gateway container
│
├── gateway :8000
│
└── 127.0.0.1:8001
        │
        ▼
   gateway container itself
        │
        X
   nothing listening
```

The desired inventory process lived in another namespace:

```text
inventory container
└── :8001
```

Therefore:

```text
127.0.0.1 inside gateway
        ≠
inventory container
```

---

# Recovering from the Localhost Failure

The incorrectly configured gateway was removed:

```bash
docker rm -f opsforge-gateway
```

Gateway was restarted using:

```bash
-e INVENTORY_URL=http://opsforge-inventory:8001
```

The host request was repeated:

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

Result:

```text
HTTP/1.1 200 OK
```

with the expected inventory data.

The failure/recovery sequence was:

```text
correct inventory service running
        ↓

gateway configured with localhost
        ↓

gateway looks inside itself
        ↓

downstream connection fails
        ↓

gateway returns HTTP 503
        ↓

restore Docker service name
        ↓

Docker DNS resolves inventory
        ↓

HTTP 200 recovered
```

---

# Failure Experiment — Broken Docker DNS Name

The next deliberate failure changed:

```text
opsforge-inventory
```

to the misspelled:

```text
opsforge-inventroy
```

Gateway was started with:

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://opsforge-inventroy:8001 \
  opsforge-gateway:a2.2
```

A direct DNS lookup was performed inside gateway:

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventroy'))"
```

Python returned:

```text
socket.gaierror: [Errno -2] Name or service not known
```

This proved the failure occurred specifically at the name-resolution layer.

The diagnostic chain was:

```text
gateway running?
        ✅

inventory running?
        ✅

same Docker network?
        ✅

destination service name correct?
        ❌

Docker DNS resolution?
        ❌
```

Root cause:

```text
misspelled service identity
```

---

# Application Behavior During DNS Failure

The host then called:

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

Gateway returned:

```text
HTTP/1.1 503 Service Unavailable
```

with:

```json
{"detail":"Inventory service unavailable"}
```

This demonstrated useful application failure handling.

The external caller did not receive a low-level Python DNS traceback.

Instead:

```text
internal DNS/service dependency failure
        ↓
gateway catches dependency failure
        ↓
HTTP 503 Service Unavailable
```

This preserves the failure surface intentionally created in A1.

---

# Recovery from DNS Failure

The misspelled gateway container was removed:

```bash
docker rm -f opsforge-gateway
```

Gateway was recreated with:

```bash
-e INVENTORY_URL=http://opsforge-inventory:8001
```

The host request was repeated:

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

Result:

```text
HTTP/1.1 200 OK
```

with:

```json
{
  "gateway": "ok",
  "inventory": {
    "item_id": "widget-456",
    "available": true,
    "quantity": 100
  }
}
```

This proved:

```text
broken DNS service name
        ↓
failure

correct DNS service name
        ↓
recovery
```

---

# Final Bridge Network State

After restoring the system, the Docker network was inspected again.

The bridge still used:

```text
Subnet:  172.20.0.0/16
Gateway: 172.20.0.1
```

Gateway was attached as:

```text
Name:        opsforge-gateway
IPv4Address: 172.20.0.3/16
```

Inventory was attached as:

```text
Name:        opsforge-inventory
IPv4Address: 172.20.0.2/16
```

The topology was:

```text
                  opsforge-net
                 172.20.0.0/16

                172.20.0.1
                    gateway
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼

      gateway container    inventory container
         172.20.0.3           172.20.0.2
            :8000                :8001
```

Application communication remained name-based:

```text
gateway
   ↓
opsforge-inventory:8001
```

rather than IP-based.

---

# Inventory Container Replacement Experiment

The current inventory IP was recorded:

```bash
docker inspect \
  opsforge-inventory \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

Result:

```text
172.20.0.2
```

Inventory was then deleted:

```bash
docker rm -f opsforge-inventory
```

and recreated:

```bash
docker run -d \
  --name opsforge-inventory \
  --network opsforge-net \
  opsforge-inventory:a2.3
```

The new IP was inspected:

```bash
docker inspect \
  opsforge-inventory \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

In this particular run Docker reassigned:

```text
172.20.0.2
```

again.

Therefore this experiment did **not** demonstrate an IP address change.

It did demonstrate an important lifecycle fact:

```text
old inventory container deleted
        ↓
new inventory container created
        ↓
same service identity reused
        ↓
Docker DNS continued resolving the service
```

A new container object replaced the original while gateway continued depending
on:

```text
opsforge-inventory
```

rather than the container's numeric address.

The design therefore does not require the application to care whether Docker
reuses the previous IP or assigns a different one in another lifecycle event.

---

# DNS Resolution After Inventory Replacement

After inventory recreation, gateway again performed:

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventory'))"
```

Result:

```text
172.20.0.2
```

Docker DNS continued resolving the logical service identity.

The important relationship is:

```text
application configuration
        ↓
opsforge-inventory
        ↓
Docker DNS
        ↓
current runtime address
```

not:

```text
application configuration
        ↓
hardcoded 172.20.0.2
```

---

# Verifying Gateway Runtime Configuration

Gateway's environment was inspected directly:

```bash
docker inspect opsforge-gateway \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep INVENTORY_URL
```

Result:

```text
INVENTORY_URL=http://opsforge-inventory:8001
```

This verified that the service address was supplied at runtime.

The application source did not need to be rewritten for Docker networking.

---

# Configuration Boundary

A1 had already introduced the concept of external runtime configuration.

A2.3 demonstrated why that decision matters.

The same application can run under different networking environments.

## A1 Host Runtime

```text
INVENTORY_URL=http://127.0.0.1:8001
```

## A2 Raw Docker Runtime

```text
INVENTORY_URL=http://opsforge-inventory:8001
```

## Future Compose Runtime

The service will later be reachable through its Compose service identity, for
example:

```text
INVENTORY_URL=http://inventory:8001
```

## Future Kubernetes Runtime

A Kubernetes Service DNS identity will eventually replace the Docker-specific
identity.

The principle remains:

```text
application behavior
        +
runtime-specific configuration
```

rather than embedding environment-specific networking knowledge in code.

---

# Internal Versus External Services

A2.3 established a useful architectural boundary.

Gateway is an entry point.

Therefore it needs host reachability during local development:

```text
Mac
 ↓
gateway
```

Inventory is an internal dependency.

External users do not need direct access to it:

```text
Mac
 X
inventory
```

Instead:

```text
gateway
 ↓
inventory
```

occurs through the internal bridge.

The architecture becomes:

```text
                     HOST

                     curl
                      │
                      ▼
               127.0.0.1:8000
                      │
                      ▼

              ─ Docker boundary ─

                      │
                      ▼
                  gateway
                    :8000
                      │
                      │ internal service call
                      ▼
                  inventory
                    :8001
```

Only the necessary entry point is host-published.

---

# Why `host.docker.internal` Is Not Used

Docker Desktop provides mechanisms such as:

```text
host.docker.internal
```

that allow a container to reach a process running on the host.

That could create:

```text
gateway container
       ↓
host.docker.internal:8001
       ↓
inventory running on Mac
```

However, this is not the intended OpsForge A2 architecture.

The goal is:

```text
gateway container
       ↓
Docker bridge
       ↓
inventory container
```

Using `host.docker.internal` for normal service communication would bypass the
container-to-container networking model that A2.3 is intended to teach.

---

# DNS as Service Discovery

Docker DNS gives connected containers a way to locate other containers using
logical names.

The gateway asks:

```text
Where is opsforge-inventory?
```

Docker resolves:

```text
opsforge-inventory
        ↓
172.20.0.2
```

The application then opens:

```text
TCP connection to 172.20.0.2:8001
```

The application only needs the stable service identity.

Conceptually:

```text
service name
    ↓
DNS
    ↓
IP address
    ↓
port
    ↓
application
```

This is the beginning of service discovery.

---

# DNS Failure Versus Connection Failure

A2.3 produced two important downstream failure modes.

## DNS Failure

Using:

```text
opsforge-inventroy
```

produced:

```text
socket.gaierror:
Name or service not known
```

The destination name could not be translated into an address.

The failure occurred at:

```text
name resolution
```

before TCP connection establishment.

---

## Connection Failure

Using:

```text
127.0.0.1:8001
```

did not require DNS resolution.

The address existed, but there was no inventory process listening at that
location inside the gateway namespace.

The failure occurred later:

```text
address known
    ↓
connect attempt
    ↓
nothing listening
    ↓
connection failure
```

These are different failure classes.

---

# Failure-Layer Model

The experiments established the following diagnostic stack:

```text
1. Container lifecycle
        ↓
Are gateway and inventory running?


2. Network attachment
        ↓
Are both containers attached to opsforge-net?


3. Service identity / DNS
        ↓
Can gateway resolve opsforge-inventory?


4. TCP reachability
        ↓
Can gateway connect to port 8001?


5. HTTP protocol
        ↓
Does inventory return an HTTP response?


6. Application behavior
        ↓
Does gateway correctly process inventory's response?
```

This layered model avoids vague diagnosis such as:

```text
"Docker networking is broken."
```

Instead, failures can be classified precisely.

---

# Recommended Diagnostic Commands

## Confirm Running Containers

```bash
docker ps
```

---

## Inspect the OpsForge Network

```bash
docker network inspect opsforge-net
```

---

## Inspect Container IP

```bash
docker inspect \
  opsforge-inventory \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

---

## Test DNS from Gateway

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventory'))"
```

---

## Test Raw HTTP from Gateway

```bash
docker exec opsforge-gateway \
  python -c \
  "import urllib.request; print(urllib.request.urlopen('http://opsforge-inventory:8001/inventory/widget-456').read().decode())"
```

---

## Inspect Gateway Runtime Environment

```bash
docker inspect opsforge-gateway \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep INVENTORY_URL
```

---

## Test Full Application Path

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

---

# Troubleshooting Table

| Symptom                                       | Diagnostic                           | Cause Observed                                | Resolution                               |
| --------------------------------------------- | ------------------------------------ | --------------------------------------------- | ---------------------------------------- |
| Inventory image build fails at `COPY`         | Inspect Docker build output          | `requirement.txt` typo                        | Correct to `requirements.txt`            |
| Gateway container name already exists         | `docker ps -a`                       | Previous stopped container retained same name | Stop/remove old container                |
| `docker run` reports invalid reference format | Inspect CLI syntax                   | Spaces around `INVENTORY_URL = ...`           | Use `INVENTORY_URL=...`                  |
| Host cannot reach `127.0.0.1:8001`            | `docker ps`, inspect published ports | Inventory intentionally not host-published    | Access internally through Docker network |
| Gateway gets HTTP 503 using `127.0.0.1:8001`  | Inspect `INVENTORY_URL`              | Gateway loopback points to gateway itself     | Use `opsforge-inventory:8001`            |
| DNS lookup raises `socket.gaierror`           | `socket.gethostbyname()`             | Misspelled `opsforge-inventroy`               | Restore `opsforge-inventory`             |
| Gateway returns 503 during DNS failure        | Test gateway endpoint                | Downstream inventory name unresolved          | Correct service identity                 |
| Gateway returns HTTP 200 after restoration    | Test gateway endpoint                | Correct DNS + network configuration           | Expected healthy behavior                |

---

# Important Command-Syntax Lesson

Environment variables supplied with `docker run -e` must use:

```text
KEY=value
```

without spaces around the equals sign.

Correct:

```bash
-e INVENTORY_URL=http://opsforge-inventory:8001
```

Incorrect:

```bash
-e INVENTORY_URL = http://opsforge-inventory:8001
```

The incorrect form changes shell/Docker argument parsing and can produce errors
before the application container starts.

---

# Container Name as Current Raw-Docker Service Identity

During this raw-Docker phase, the inventory container was explicitly named:

```text
opsforge-inventory
```

and Docker DNS resolved this identity on the user-defined network.

Therefore gateway used:

```text
http://opsforge-inventory:8001
```

This is sufficient for learning raw Docker networking.

Later Docker Compose will replace much of this manual lifecycle management with
declarative service definitions and service names.

---

# Why Raw Docker Is Becoming Cumbersome

A2.3 required manually managing:

```text
docker network create
docker build
docker run
container names
network attachment
environment variables
port publishing
service addresses
container deletion
container recreation
failure recovery
```

For only two application services, the command surface has already become
significant.

OpsForge ultimately contains five runtime components:

```text
gateway
inventory
worker
PostgreSQL
Redis
```

Managing them entirely with individual `docker run` commands would become
error-prone.

This is the problem Docker Compose will solve later in A2.

Compose should therefore be understood as:

```text
declarative automation
of container runtime relationships
```

not as a replacement for understanding Docker networking.

---

# Relationship to Kubernetes

A2.3's service-discovery model prepares for Kubernetes.

Docker currently provides:

```text
container
    ↓
Docker DNS
    ↓
container/service identity
```

Kubernetes will later provide:

```text
Pod
    ↓
Kubernetes DNS
    ↓
Service
    ↓
destination Pod(s)
```

The implementation differs, but the architectural principle remains:

> Applications should depend on stable service identities rather than ephemeral
> workload IP addresses.

The Docker experiment therefore establishes a foundation for understanding:

* Kubernetes Service discovery,
* ClusterIP,
* Service DNS,
* Pod IP ephemerality,
* internal application networking,
* and eventually NetworkPolicy.

---

# A2.3 Final Runtime Architecture

The validated architecture is:

```text
                         macOS HOST

                             │
                             │ curl
                             ▼
                     127.0.0.1:8000
                             │
                             │ published port
                             ▼

┌──────────────────────────────────────────────────────┐
│                  Docker Runtime                      │
│                                                      │
│                  opsforge-net                        │
│                 172.20.0.0/16                        │
│                                                      │
│  ┌────────────────────────┐                          │
│  │ opsforge-gateway       │                          │
│  │                        │                          │
│  │ IP: 172.20.0.3         │                          │
│  │ port: 8000             │                          │
│  │                        │                          │
│  │ INVENTORY_URL=         │                          │
│  │ http://opsforge-       │                          │
│  │ inventory:8001        │                          │
│  └───────────┬────────────┘                          │
│              │                                       │
│              │ DNS: opsforge-inventory               │
│              │ HTTP :8001                            │
│              ▼                                       │
│  ┌────────────────────────┐                          │
│  │ opsforge-inventory     │                          │
│  │                        │                          │
│  │ IP: 172.20.0.2         │                          │
│  │ port: 8001             │                          │
│  │ host port: none        │                          │
│  └────────────────────────┘                          │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

# Reproducible A2.3 Commands

## Build Inventory

```bash
docker build \
  -f docker/inventory.Dockerfile \
  -t opsforge-inventory:a2.3 \
  .
```

---

## Validate Inventory Import

```bash
docker run --rm \
  opsforge-inventory:a2.3 \
  python -c \
  "import app.inventory.main; print('inventory import ok')"
```

---

## Create Bridge Network

```bash
docker network create opsforge-net
```

---

## Inspect Network

```bash
docker network inspect opsforge-net
```

---

## Run Internal Inventory

```bash
docker run -d \
  --name opsforge-inventory \
  --network opsforge-net \
  opsforge-inventory:a2.3
```

---

## Verify Inventory Is Not Published to Host

```bash
curl http://127.0.0.1:8001/inventory/widget-456
```

Expected:

```text
connection failure
```

---

## Resolve Inventory Through Docker DNS

```bash
docker run --rm \
  --network opsforge-net \
  python:3.13-slim \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventory'))"
```

---

## Test Inventory HTTP Internally

```bash
docker run --rm \
  --network opsforge-net \
  python:3.13-slim \
  python -c \
  "import urllib.request; print(urllib.request.urlopen('http://opsforge-inventory:8001/inventory/widget-456').read().decode())"
```

---

## Start Correct Gateway

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://opsforge-inventory:8001 \
  opsforge-gateway:a2.2
```

---

## Test DNS from Gateway

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventory'))"
```

---

## Test HTTP from Gateway

```bash
docker exec opsforge-gateway \
  python -c \
  "import urllib.request; print(urllib.request.urlopen('http://opsforge-inventory:8001/inventory/widget-456').read().decode())"
```

---

## Test End-to-End Request

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

Expected:

```text
HTTP/1.1 200 OK
```

---

## Deliberately Break with Localhost

```bash
docker rm -f opsforge-gateway
```

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://127.0.0.1:8001 \
  opsforge-gateway:a2.2
```

Then:

```bash
curl -i \
  http://127.0.0.1:8000/check-inventory/widget-456
```

Expected:

```text
HTTP/1.1 503 Service Unavailable
```

---

## Restore Service Name

```bash
docker rm -f opsforge-gateway
```

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://opsforge-inventory:8001 \
  opsforge-gateway:a2.2
```

---

## Deliberately Break DNS

```bash
docker rm -f opsforge-gateway
```

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://opsforge-inventroy:8001 \
  opsforge-gateway:a2.2
```

Then:

```bash
docker exec opsforge-gateway \
  python -c \
  "import socket; print(socket.gethostbyname('opsforge-inventroy'))"
```

Expected:

```text
socket.gaierror:
Name or service not known
```

---

## Restore DNS Again

```bash
docker rm -f opsforge-gateway
```

```bash
docker run -d \
  --name opsforge-gateway \
  --network opsforge-net \
  -p 127.0.0.1:8000:8000 \
  -e INVENTORY_URL=http://opsforge-inventory:8001 \
  opsforge-gateway:a2.2
```

---

## Inspect Runtime Environment

```bash
docker inspect opsforge-gateway \
  --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep INVENTORY_URL
```

Expected:

```text
INVENTORY_URL=http://opsforge-inventory:8001
```

---

# A2.3 Evidence Summary

| Experiment                                                   | Observed Result |
| ------------------------------------------------------------ | --------------- |
| Inventory Dockerfile created                                 | ✅               |
| Initial inventory build failed due to `requirement.txt` typo | ✅ diagnosed     |
| Dockerfile corrected to `requirements.txt`                   | ✅               |
| `opsforge-inventory:a2.3` built successfully                 | ✅               |
| Inventory Python import verified inside image                | ✅               |
| User-defined `opsforge-net` bridge created                   | ✅               |
| Bridge subnet observed as `172.20.0.0/16`                    | ✅               |
| Bridge gateway observed as `172.20.0.1`                      | ✅               |
| Inventory attached to `opsforge-net`                         | ✅               |
| Inventory received `172.20.0.2`                              | ✅               |
| Inventory remained unpublished to host                       | ✅               |
| Host request to `127.0.0.1:8001` failed                      | ✅ expected      |
| Docker DNS resolved `opsforge-inventory` to `172.20.0.2`     | ✅               |
| Internal HTTP request to inventory succeeded                 | ✅               |
| Previous gateway container name caused runtime conflict      | ✅ diagnosed     |
| Gateway attached to same bridge                              | ✅               |
| Gateway received `172.20.0.3`                                | ✅               |
| Gateway DNS lookup for inventory succeeded                   | ✅               |
| Gateway direct HTTP request to inventory succeeded           | ✅               |
| End-to-end host → gateway → inventory returned HTTP 200      | ✅               |
| Using `127.0.0.1:8001` from gateway failed                   | ✅ expected      |
| Gateway converted dependency failure into HTTP 503           | ✅               |
| Restoring Docker service name returned HTTP 200              | ✅               |
| Misspelled `opsforge-inventroy` produced `socket.gaierror`   | ✅               |
| DNS failure produced gateway HTTP 503                        | ✅               |
| Correct service identity restored healthy traffic            | ✅               |
| Inventory container deleted and recreated                    | ✅               |
| Docker reused `172.20.0.2` during this particular recreation | ✅ observed      |
| DNS continued resolving recreated inventory                  | ✅               |
| Gateway runtime `INVENTORY_URL` verified through inspect     | ✅               |
| Application avoided hardcoded inventory IP                   | ✅               |

---

# Key Lessons

## 1. `127.0.0.1` Is Namespace-Local

Inside gateway:

```text
127.0.0.1
=
gateway
```

Inside inventory:

```text
127.0.0.1
=
inventory
```

Loopback does not cross container boundaries.

---

## 2. Container-to-Container Communication Does Not Require Host Publishing

Inventory successfully served gateway without:

```text
-p 8001:8001
```

Internal services can remain internal.

---

## 3. User-Defined Bridges Provide Container Connectivity

Both application containers joined:

```text
opsforge-net
```

which provided a shared internal network.

---

## 4. Docker DNS Provides Service Discovery

Gateway could resolve:

```text
opsforge-inventory
```

without knowing inventory's numeric IP.

---

## 5. Hardcoded Container IPs Are the Wrong Abstraction

Even though inventory used:

```text
172.20.0.2
```

during these experiments, gateway depended on:

```text
opsforge-inventory
```

instead.

---

## 6. DNS Failures and Connection Failures Are Different

```text
opsforge-inventroy
```

failed during name resolution.

```text
127.0.0.1:8001
```

resolved immediately but pointed to the wrong network namespace.

Understanding the difference makes diagnosis faster.

---

## 7. Runtime Configuration Keeps Application Code Portable

Gateway did not need source-code changes.

Only:

```text
INVENTORY_URL
```

changed between runtime environments.

---

## 8. HTTP 503 Represented Dependency Unavailability

Gateway translated downstream connectivity and DNS failures into:

```text
503 Service Unavailable
```

rather than exposing internal implementation errors to the caller.

---

## 9. Docker CLI Errors Must Be Separated from Runtime Errors

The malformed:

```text
INVENTORY_URL = ...
```

command failed before application runtime.

That was a shell/Docker command syntax problem, not service networking.

---

## 10. Container Names Are More Useful Than Ephemeral Addresses

Service identity:

```text
opsforge-inventory
```

is the abstraction consumed by gateway.

Docker handles translation to the current runtime address.

---

# Mental Model After A2.3

The networking model has evolved from:

```text
A1

gateway
   ↓
127.0.0.1:8001
   ↓
inventory
```

to:

```text
A2.3

gateway container
   ↓
service identity
   ↓
Docker DNS
   ↓
bridge network
   ↓
inventory container
```

The complete local request path is now:

```text
client
  ↓
host published gateway port
  ↓
gateway container
  ↓
runtime INVENTORY_URL
  ↓
Docker DNS
  ↓
opsforge-inventory
  ↓
internal bridge network
  ↓
inventory :8001
  ↓
response
```

---

# Transition Forward

A2.3 established manual container networking between gateway and inventory.

The current runtime is still manually managed with:

```text
docker build
docker network create
docker run
docker rm
environment variables
container names
port mappings
network attachment
```

The next stages of A2 will extend this model to:

```text
gateway
inventory
worker
PostgreSQL
Redis
```

and eventually move the entire topology into Docker Compose.

Before Compose becomes the canonical runtime, the underlying concepts must
remain clear:

```text
process
container
network namespace
bridge
DNS
service identity
port
runtime configuration
dependency health
```

A2.3 therefore provides the service-discovery and internal-networking
foundation required for the full five-component OpsForge container runtime.

