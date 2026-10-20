# Learner-code runner: threat model and deployment gate

## Status

**Untrusted learner-code execution is not approved for public deployment.** The
current `app/sandbox.py` AST allowlist and child process are defense-in-depth
measures, not a security boundary. The application now fails closed by default:
`CODE_EXECUTION_ENABLED` defaults to `false`, code levels cannot be started
while it is false, and production configuration rejects setting it to `true`.
Do not remove this gate before an independent security review accepts the
remaining risks or the executor is replaced by a stronger isolation design.

## Threat model

Treat every submitted program as intentionally hostile. An authenticated user
may attempt to read application secrets or files, reach the network, escape the
Python-level allowlist, consume CPU or memory, create processes, fill pipes,
cause serialization failures, or exhaust worker capacity. A compromised child
must not be able to affect other users, the API process, the host, databases,
deployment credentials, or other workloads.

The input-size check, AST validation, restricted builtins, child process,
CPU-time limit, and attempted address-space limit reduce some risks. They do
**not** prove confinement. In particular, Python AST restrictions are not an
OS security boundary; the current runner inherits the parent process's user,
environment, filesystem view, and network access. The pipe/IPC protocol and
process lifecycle need further review. The child can also inherit sensitive
state through the process environment or file descriptors.

## Platform support and limitations

The current implementation imports the Unix-only `resource` module and uses
`SIGALRM`, `RLIMIT_CPU`, `RLIMIT_AS`, and a `fork` multiprocessing context when
available. It is therefore intended only for Unix-like development/test
environments and is not portable to native Windows. Resource-limit semantics
vary by OS and runtime; `RLIMIT_AS` is not consistently available or enforced,
and CPU limits are not a substitute for wall-clock supervision. Do not claim
equivalent protection across Linux, macOS, Windows, containers, or hosting
providers.

CI regression tests exercise the existing behavior on a disposable
GitHub-hosted Linux runner. They are not a penetration test and do not prove
the runner is safe.

## Required design before public execution

Prefer a separate disposable worker or container/VM per execution with:

- non-root UID/GID and no application credentials or inherited secrets;
- network disabled at the OS/container layer, not merely blocked in Python;
- read-only minimal root filesystem and a small dedicated writable temporary
  directory with size limits;
- hard CPU, wall-clock, memory, process-count, file-size, and open-file limits;
- no host sockets, Docker socket, cloud metadata access, or sensitive mounts;
- bounded input and output, robust IPC that cannot deadlock on large output,
  and guaranteed cleanup/reaping of all descendants on timeout;
- per-job isolation, concurrency/rate limits, and monitoring of failures.

Run the worker under a separately reviewed isolation policy. Test on disposable
infrastructure designed for hostile-code testing; never run escape or resource
exhaustion experiments on a personal workstation or production host.

## Regression coverage

`tests/test_sandbox.py` covers representative rejected syntax/private
attributes, malformed input, supported benign code, oversized submissions,
memory pressure, and CPU-heavy expressions. These tests are useful regression
checks, not proof of security. Network isolation, filesystem confidentiality,
process-creation controls, IPC deadlocks, child-process cleanup, and cross-OS
behavior remain unresolved until tested under the proposed OS-level boundary.

## Release gate

Before enabling public code execution:

1. Replace or wrap this runner in the reviewed OS/container/VM boundary.
2. Demonstrate no network access, no secrets/filesystem access, bounded resource
   consumption, bounded output/IPC, and descendant cleanup on timeout.
3. Test the supported deployment OS/runtime with repeatable isolated tests.
4. Obtain and record an independent security review and explicit risk
   acceptance.
5. Keep `CODE_EXECUTION_ENABLED=false` in production until all gates pass.
