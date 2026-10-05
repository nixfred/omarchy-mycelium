# Installation

## New Git-managed installation

Use the Omarchy plugin CLI in a normal desktop terminal:

```bash
omarchy plugin add https://github.com/nixfred/omarchy-mycelium.git --enable
```

The manifest ID is `nixfred.mycelium`. The plugin has a service, an explicit overlay and a bar widget. Add clones the repository into your Omarchy plugin directory; `--enable` requests enabling it after Omarchy's prompts. Its default bar section is right. Future updates use:

```bash
omarchy plugin update nixfred.mycelium
```

You can review before enabling by omitting `--enable`, then run `omarchy plugin enable nixfred.mycelium` yourself. Disabling uses `omarchy plugin disable nixfred.mycelium`. The shell discovers the versioned v3 QML entry points; no whole-shell restart is part of the normal install route.

## Source checkout

```bash
git clone https://github.com/nixfred/omarchy-mycelium.git
cd omarchy-mycelium
python3 tools/verify-runtime.py
omarchy plugin validate .
```

For a clean destination, Omarchy also documents manual installation: place only the runtime files listed by `tools/runtime-hashes.json` in `~/.config/omarchy/plugins/nixfred.mycelium/`, run `omarchy-shell shell rescanPlugins`, then `omarchy plugin enable nixfred.mycelium`. There is no `omarchy plugin install` command. Manual copies are not Git-managed and cannot use `plugin update` as a Git pull.

## Existing manual installation

`plugin add` refuses an existing plugin destination. Do not overwrite an active plugin with a repository clone or restore an old whole shell configuration. First preserve the current plugin and its current placement/settings. Use a separately coordinated, Mycelium-only update that unloads the old service, places the validated v3 runtime with the manifest last, rescans plugins, and restores the freshly captured configuration through the shell's `compareAndSetShellConfig` API. This avoids resetting the user's bar order or racing another plugin update.

The development desktop's manually installed v2 has not yet been activated to v3. Its local manual-update helper and private backup records are intentionally not shipped in this public repository. The public runtime is tested; no live v3 activation outcome is claimed.
