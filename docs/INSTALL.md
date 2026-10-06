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

You can review before enabling by omitting `--enable`, then run `omarchy plugin enable nixfred.mycelium` yourself. Disabling uses `omarchy plugin disable nixfred.mycelium`. The shell discovers the versioned v4 QML entry points; no whole-shell restart is part of the normal install route.

## Source checkout

```bash
git clone https://github.com/nixfred/omarchy-mycelium.git
cd omarchy-mycelium
python3 tools/verify-runtime.py
omarchy plugin validate .
```

For a clean destination, Omarchy also documents manual installation: place only the runtime files listed by `tools/runtime-hashes.json` in `~/.config/omarchy/plugins/nixfred.mycelium/`, run `omarchy-shell shell rescanPlugins`, then `omarchy plugin enable nixfred.mycelium`. There is no `omarchy plugin install` command. Manual copies are not Git-managed and cannot use `plugin update` as a Git pull.

## Existing manual installation

`plugin add` refuses an existing plugin destination. Do not overwrite an active plugin with a repository clone or restore an old whole shell configuration. First preserve the current plugin and its current placement/settings. Update the plugin in place instead: copy the validated `v4/` folder and `bridge.py` first, then `manifest.json` last, so the shell switches entry points once. The plugin ID does not change, so the bar widget keeps its place and settings. Older `v2/` or `v3/` folders can be removed afterwards. Restart the shell once (`omarchy restart shell`) so the plugin's IPC target is fresh.

