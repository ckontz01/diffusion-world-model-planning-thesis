# Desktop Commander tool-discovery investigation

Date: 6 September 2026. Scope: connection reliability, not scientific changes.

## Findings observed in this conversation

The preceding turn's discovery returned 21 combined Desktop Commander / Plugin
Management actions and did not expose terminal execution. This turn returned
36 combined actions, including start_process and interact_with_process.
These are ChatGPT-facing discovery counts, not captures of the hosted server's
raw tools/list response. The precise reason for the difference is unavailable.

Without reinstalling, restarting the agent, changing app permissions, editing
its configuration, or approving an administrator operation, start_process ran
a simple probe and the established WSL-to-Prometheus SSH command successfully.
At 18:45:06 UTC, the remote response identified controller1 / ckontzias, with
393 stage-0 tasks complete, two running and 55 pending resources.

The device reported online with valid authentication. Installed agent version
is 0.2.48, Node 24.11.1, Windows, default shell powershell.exe. The local MCP
process PID 13308 started at 2026-09-05T21:14:02.5859350Z and was still running.
No restart or local version change was required for the command tools to return.

The app-specific permission is Use my default; its effective default is Allow
low-risk actions. This setting was read, not changed. Command availability
under this setting was demonstrated; this is not evidence that every command
will be approved. Some installed command restrictions intentionally concern
administrative operations. No security restrictions were removed.

## Installed-source inspection

In dist/server.js, shouldIncludeTool (lines 205-216) excludes only feedback and
onboarding tools for a particular desktop-app client. It does not suppress
start_process. The tools array includes start_process (line 791); its declared
annotations (lines 855-860) are readOnlyHint=false, destructiveHint=true and
openWorldHint=true. These correctly describe an arbitrary terminal capability,
not the risk of each individual status command. They are not relabelled here.

The remote-device integration's listClientTools (lines 131-153) forwards the
local MCP listTools result, or an empty list on a listing error. No selective
read-only filtering was found in that function. This does not audit the hosted
relay or ChatGPT's private tool-selection, policy, cache or authorization logs.

Installed source SHA-256:
- dist/server.js: 3bc0962a60ff74b5c8a95e1627cb1e8fcb87e5a1bee19426c9e73f5107f84428
- dist/remote-device/desktop-commander-integration.js: dad8505857b7393cea5d681cdc22612da91fcc5b77a6556df00931ca078760ee
- dist/remote-device/device.js: 02cd9f6cdfa65a63c93fe709675499e2d0a265561d277078f7201c4d540a2509

Inference: the observed missing-action condition was in the tool exposure /
discovery path before local command execution, not a demonstrated SSH outage
or a disappeared local terminal implementation. The exact responsible layer
(ChatGPT selection/policy/cache, connector, or hosted relay) remains unresolved.
No permanent provider-side fix or guarantee against recurrence is claimed.
A successful new discovery does not prove that discovery itself caused recovery.

Session label Blocked:true describes a process waiting for input; it must not
be used as evidence of a security refusal. Ping success likewise proves device
reachability, not successful SSH or current experiment completion.

## Recovery procedure and new operational helper

1. Discover the named terminal action. If missing, inspect the full app inventory
   once, device health and the effective permissions. Record the missing layer;
   do not repeatedly change query wording or invent a terminal result.
2. If available and authorized, use check_prometheus_readonly.ps1 through
   start_process. It fixes the route to Thesis-Ubuntu/chris -> ssh prometheus,
   strict host-key checking and noninteractive authentication. It invokes only
   fixed status queries, with a bounded local-client timeout and no outcome read.
3. Distinguish an absent tool, a denied invocation, a shell error and an SSH
   failure. Do not substitute Windows ssh when the working alias/keys are in WSL.
4. If the tool is still absent but the device responds, refresh/reselect the app
   in the supported ChatGPT UI or use a fresh conversation with this recovery
   context. This is a troubleshooting step, not a proved permanent remedy.
5. If it recurs, give OpenAI/Desktop Commander support the times, discovery
   counts, agent version/PID and sanitized report. Do not send credentials.

The helper is not a replacement or bypass for missing/denied terminal access.
No provider implementation, app permission, OS security setting or experiment
source was changed. No new recurring process or Slurm job was installed.
PowerShell parser validation and seven static safety/route checks passed.
The live helper at 18:52:45 UTC returned exit 0, 394 sealed first-stage tasks,
two running, 54 pending resources, and no verifier or terminal files yet.
Presence of such files alone would not validate their contents.
One earlier diagnostic PowerShell command had a foreach/pipeline parse error;
it executed no operations and was corrected. It was not a tool-discovery error.
