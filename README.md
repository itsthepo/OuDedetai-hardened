> [!IMPORTANT]
> **This is an unofficial, security-hardened fork** of
> [FaithLife-Community/OuDedetai](https://github.com/FaithLife-Community/OuDedetai).
> It is not made or supported by FaithLife or the OuDedetai maintainers. What it
> changes and why is in [HARDENING.md](HARDENING.md).
>
> There are **no prebuilt binaries** here: you build it yourself (a few minutes,
> steps below). **Don't use the `wget …/releases/latest/download/oudedetai`
> command further down this page.** It downloads upstream's normal binary, which
> doesn't have these fixes.

## Installing this fork (Arch Linux / EndeavourOS)

**1. Install git and podman.** The build runs in a throwaway container, so it
installs no Python or build tools on your system:

```bash
sudo pacman -S --needed git podman
```

Rootless podman needs subordinate user and group ID ranges for your user. Check them:

```bash
grep "^$USER:" /etc/subuid /etc/subgid
```

If either file has no line for you, add a range and restart podman's state:

```bash
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 "$USER"
podman system migrate
```

**2. Clone and build:**

```bash
git clone https://github.com/itsthepo/OuDedetai-hardened.git
cd OuDedetai-hardened
scripts/hardened-build.sh
```

This builds only the committed source in a disposable Fedora container, runs the
hardening tests, and writes `dist/oudedetai` along with its SHA-256. The container
image stays in podman's cache. Remove it with
`podman image rm registry.fedoraproject.org/fedora:45` if you like.

**3. Run the installer:**

```bash
DIALOG=tk ./dist/oudedetai
```

What to expect:

- **Before anything runs as root, the installer shows the exact commands and asks
  first.** On Arch it runs `pacman -Syu --noconfirm --needed <packages>`, which is
  a **full system upgrade** plus the missing dependencies (fuse2, samba, 7zip,
  cabextract, audio/video libraries, …). That is normal for Arch, where partial
  upgrades aren't supported, but expect it to take a while.
- It asks for your password through polkit (`pkexec`). EndeavourOS desktops ship
  a polkit agent. On a bare window-manager setup, make sure one is running.
- It copies itself to `~/.local/share/FaithLife-Community/oudedetai/oudedetai` and
  adds menu entries for Logos and for the Ou Dedetai control panel.
- Only the **Logos 10** installer is pinned. To install Verbum or a different Logos
  release, see "Current pins" in [HARDENING.md](HARDENING.md).
- Self-update is turned off. Update with the steps below.

### Updating

When this fork takes in an upstream update, the `hardened` branch is **rewritten**
(rebased), so a plain `git pull` will fail. Instead run:

```bash
cd OuDedetai-hardened
git fetch && git reset --hard origin/hardened   # discards any local edits in this clone
scripts/hardened-build.sh

D=~/.local/share/FaithLife-Community/oudedetai
install -m 0755 dist/oudedetai "$D/oudedetai.new" && mv -f "$D/oudedetai.new" "$D/oudedetai"
"$D/oudedetai" --create-shortcuts
```

---

*The rest of this page is upstream's README.*

[![GitHub All Releases](https://img.shields.io/github/downloads/FaithLife-Community/OuDedetai/total.svg)]()
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f730f74748c348cb9b3ff2fa1654c84b)](https://app.codacy.com/manual/FaithLife-Community/OuDedetai?utm_source=github.com&utm_medium=referral&utm_content=FaithLife-Community/OuDedetai&utm_campaign=Badge_Grade_Dashboard)
[![Automation testing](https://img.shields.io/badge/Automation-testing-sucess)](https://github.com/FaithLife-Community/LogosLinuxInstallTests) [![Installer LogosBible](https://img.shields.io/badge/Installer-LogosBible-blue)](https://www.logos.com) [![LastRelease](https://img.shields.io/github/v/release/FaithLife-Community/OuDedetai)](https://github.com/FaithLife-Community/OuDedetai/releases)

# Ou Dedetai

>Remember Jesus Christ, risen from the dead, the offspring of David, as preached in my gospel, for which I am suffering, bound with chains as a criminal. But **the word** of God **is not bound!**
>
>ἀλλʼ **ὁ λόγος** τοῦ θεοῦ **οὐ δέδεται**  

—Second Timothy 2:8–9 [ESV](https://biblia.com/bible/esv/2-timothy/2/8-9), [NA<sup>28</sup>](https://biblia.com/bible/ubs5/2-timothy/2/9)

## Manages Logos Bible Software via Wine

This repository contains a Python program for installing and maintaining [FaithLife](https://faithlife.com/)'s [Logos Bible (Verbum) Software](https://www.logos.com/) via [Wine](https://www.winehq.org/).

This program is created and maintained by the FaithLife Community and is licensed under the MIT License.

## oudedetai binary

The main program is a distributable executable binary and contains Python itself and all necessary Python packages.

When running the program, it will attempt to determine your operating system and package manager.
It will then attempt to install all needed system dependencies during the installation of Logos.
When the installation is finished, it will place two shortcuts on your computer: one will launch Logos directly; the other will launch the Control Panel.

To access the GUI version of the program, double-click the executable in your file browser or on your desktop, and then follow the prompts.

The program can also be run from source and should be run from a Python virtual environment.
See below.

## Install Guide (for users)

For an installation guide with pictures and video, see the wiki's [Install Guide](https://github.com/FaithLife-Community/OuDedetai/wiki/Install-Guide).

In Summary:
```bash
wget https://github.com/FaithLife-Community/OuDedetai/releases/latest/download/oudedetai
chmod +x ./oudedetai
DIALOG=tk ./oudedetai
```

NOTE: You can run **Ou Dedetai** using the Steam Proton Experimental binary, which often has the latest and greatest updates to make Logos run even smoother. The script should be able to find the binary automatically, unless your Steam install is located outside of your HOME directory.

If you want to install your distro's dependencies outside of the script, please see the [System Dependencies wiki page](https://github.com/FaithLife-Community/OuDedetai/wiki/System-Dependencies).

---

Soli Deo Gloria
