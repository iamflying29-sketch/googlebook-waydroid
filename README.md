# Waydroid on the Googlebook

This project documents how I run Waydroid, a complete Android 13 system with Google Play, inside the Linux
Terminal of a Lenovo Googlebook 15. It covers the network fix that lets Android boot in the Linux Terminal's
virtual machine, the settings that keep it running smoothly, registering the system with Google so Play sign-in
works, and two launcher buttons. The repository contains the two launcher commands, `waydroid-open` and
`waydroid-restart`, the configuration files I use, and a helper that makes the launcher icons.

## What it does

I run Waydroid 1.6.2 with a LineageOS 20 (Android 13) image that includes Google Play, inside the Debian 13
virtual machine of the Googlebook's Linux Terminal. My setup includes Intel's ARM translator (libhoudini), so
Waydroid can install Android apps that only come in ARM versions, including 32-bit ARM apps that GooglebookOS
itself cannot run.

Two buttons on the panel of the Linux Terminal's display open Waydroid and restart it. The same actions are
available as the terminal commands `waydroid-open` and `waydroid-restart`.

## The problem

I wanted to run ARM-only Google Play apps on the x86 Googlebook. GooglebookOS can already translate 64-bit ARM
apps (its supported ABIs are `x86_64` and `arm64-v8a`), but it has no support for 32-bit ARM apps. Waydroid had
been installed in the Linux Terminal, together with the Google Play image and the libhoudini ARM translation
overlay, but Android never finished starting.

The cause was Waydroid's network setup. Waydroid's log showed the same failure on every start:

```
Warning: Extension CHECKSUM revision 0 not supported, missing kernel module?
iptables: No chain/target/match by that name.
Failed to setup waydroid-net.
RuntimeError: Command failed: % /usr/lib/waydroid/data/scripts/waydroid-net.sh start
```

Waydroid's network script, `/usr/lib/waydroid/data/scripts/waydroid-net.sh`, uses iptables by default. One of
its rules uses the iptables `CHECKSUM` target:

```
iptables -t mangle -A POSTROUTING -o waydroid0 -p udp -m udp --dport 68 -j CHECKSUM --checksum-fill
```

The Linux Terminal's kernel is built without that feature (`# CONFIG_NETFILTER_XT_TARGET_CHECKSUM is not set` in
`/proc/config.gz`). The network script failed, and Waydroid gave up before Android could boot. The unused LXC
network service, `lxc-net.service`, failed in the same way. The kernel does fully support nftables
(`CONFIG_NF_TABLES`, `CONFIG_NFT_NAT` and `CONFIG_NFT_MASQ` are all built in).

Three more problems appeared after that:

- **Auto-freeze.** Waydroid's configuration had `suspend_action = freeze`. Waydroid froze Android whenever its
  window was not visible, which also stopped Play Store downloads.
- **Memory.** The virtual machine has 3.8 GB of RAM. With Android running, the Play Store alone used about 670 MB,
  and the 1 GB compressed swap (zram) was 97% full, so Android looked frozen.
- **Google Play sign-in.** Google Play refused to sign in until the system was registered with Google, because a
  Waydroid system is not a certified device.

## How I solved it

1. **I switched the network script to nftables.** I installed the `nftables` package, saved the original script
   as `waydroid-net.sh.orig`, and changed one line from `LXC_USE_NFT="false"` to `LXC_USE_NFT="true"`. The script
   then set up the bridge, the NAT rule and DHCP without errors. Android booted in about 18 seconds, with working
   internet, the Play Store and Google Play Services. Android reported the ABIs
   `x86_64,x86,arm64-v8a,armeabi-v7a,armeabi` and the native bridge `libhoudini.so`.

2. **I made the change survive upgrades.** A Waydroid package upgrade replaces the network script and would
   undo the change. A systemd drop-in for `waydroid-container.service` runs the same one-line edit every time the
   service starts, so the fix is re-applied automatically.

3. **I turned off the failing LXC network service.** Waydroid does not use `lxc-net.service`, so I disabled it.

4. **I turned off auto-freeze.** I set the Waydroid property `persist.waydroid.suspend` to `false`, so Android
   keeps running in the background. This command has to run as the Linux account that owns the Waydroid session,
   not as root. With `sudo` it fails, because root has no Waydroid session.

5. **I added a swap file.** I added a 4 GB swap file, `/swapfile-waydroid`, at priority 5, which is lower than the
   fast compressed swap (priority 100). The kernel uses the compressed swap first and the file only when that is
   full. After a restart, Android had about 1.9 GB of RAM and 4.8 GB of swap free, which was enough for the Play
   Store to run smoothly.

6. **I registered the system with Google.** I read Waydroid's Google Services Framework Android ID and
   registered it on Google's official device registration page. After a restart of Waydroid, I could sign in to
   Google Play.

7. **I added two launcher buttons.** `waydroid-open` shows the Waydroid window and starts Android first if
   needed. `waydroid-restart` fully restarts Android. I made 32-pixel icons from Waydroid's own icon and added both
   commands as launchers on the Weston panel of the Linux Terminal's display. I tested the restart button: Android
   came back in about 20 seconds, and Android's core process had been running for only 22 seconds afterwards, so
   it really restarted.

An app that ships only with 64-bit ARM libraries installed successfully from Waydroid's Play Store, but I have
not launched and tested any ARM app yet. See [Limitations and known issues](#limitations-and-known-issues).

## Requirements

- A Lenovo Googlebook 15 (mine has an Intel Core Ultra 5 325). I tested on GooglebookOS build
  `CL3B.260622.271.R1` (Android 17).
- The Linux Terminal with its graphical display. My virtual machine runs Debian 13 (trixie) with kernel
  `6.12.93-android16` on x86_64, 8 CPU cores and 3.8 GB of RAM. The Linux Terminal's user has passwordless
  `sudo`, which the launcher commands rely on (`sudo -n`).
- Disk space: about 3.2 GB for the Android images (the system image is 2.6 GB and the vendor image 0.56 GB), 4 GB
  for the swap file, and room for Android apps and data.
- Waydroid 1.6.2 from the official Waydroid repository, and the packages `nftables`, `git`, `lzip`,
  `python3-venv` and `python3-pil`. The installation steps install them.
- A Google account for Google Play.
- adb is not needed for this project.

## Installation

The general Linux Terminal setup is in the shared
[Getting Started guide](https://github.com/iamflying29-sketch/googlebook-projects/blob/main/GETTING-STARTED.md).
Every Waydroid-specific step is below. Run the commands in the Linux Terminal.

1. **Download this repository.**

   ```
   cd ~
   git clone https://github.com/iamflying29-sketch/googlebook-waydroid.git
   ```

2. **Install Waydroid.** Follow the official instructions at
   <https://docs.waydro.id/usage/install-on-desktops>. For Debian they currently are:

   ```
   sudo apt install curl ca-certificates
   curl -s https://repo.waydro.id | sudo bash
   sudo apt install waydroid
   ```

   The second command adds Waydroid's package repository. On my system it added this line to the apt sources:
   `deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ trixie main`.

3. **Download the Android image with Google Play.**

   ```
   sudo waydroid init -s GAPPS
   ```

   My image is `20.0-20260927-GAPPS-waydroid_x86_64` (LineageOS 20, Android 13) with the `MAINLINE` vendor image.

4. **Switch Waydroid's network script to nftables.**

   ```
   sudo apt install nftables
   S=/usr/lib/waydroid/data/scripts/waydroid-net.sh
   sudo cp -n "$S" "$S.orig"
   sudo sed -i 's/^LXC_USE_NFT="false"/LXC_USE_NFT="true"/' "$S"
   grep -n '^LXC_USE_NFT' "$S"
   ```

   The last command should print `LXC_USE_NFT="true"` (on line 28 in Waydroid 1.6.2). The change is shown in
   `config/waydroid-net-nft.diff`. The `nftables` package is required: the script uses nftables only when the
   `nft` command exists, `nft list ruleset` works, and `LXC_USE_NFT` is `true`. Otherwise it silently falls back to
   iptables and fails again.

5. **Install the systemd drop-in that re-applies the change at every start.**

   ```
   cd ~/googlebook-waydroid
   sudo mkdir -p /etc/systemd/system/waydroid-container.service.d
   sudo cp config/use-nft.conf /etc/systemd/system/waydroid-container.service.d/
   sudo systemctl daemon-reload
   systemctl cat waydroid-container | grep ExecStartPre
   ```

6. **Turn off the failing LXC network service.** If `systemctl --failed` lists `lxc-net.service`, disable it:

   ```
   sudo systemctl disable --now lxc-net
   sudo systemctl reset-failed
   ```

7. **Add the libhoudini ARM translation layer.** Waydroid's own image has no ARM translation. The third-party
   tool [casualsnek/waydroid_script](https://github.com/casualsnek/waydroid_script) is a Python script that adds
   extras to Waydroid, such as GApps, Magisk, the libndk or libhoudini ARM translation layers, microG and Widevine,
   and it can also print the Android ID used for registration. Its README describes its libhoudini option as
   Intel's libhoudini, taken from Microsoft's Windows Subsystem for Android image. Clone it into your home folder:

   ```
   sudo apt install git lzip python3-venv
   cd ~
   git clone https://github.com/casualsnek/waydroid_script
   cd waydroid_script
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   sudo venv/bin/python3 main.py install libhoudini
   ```

   Keep the tool in your Linux home folder. A virtual environment that I created in the folder that the Linux
   Terminal shares with GooglebookOS had no `bin` folder and did not work. If the tool's options have changed, follow its own
   README.

8. **Add the 4 GB swap file.** `swapon` and `mkswap` live in `/sbin`, which is not on the normal user's `PATH`, so
   the full paths are used:

   ```
   sudo fallocate -l 4G /swapfile-waydroid
   sudo chmod 600 /swapfile-waydroid
   sudo /sbin/mkswap /swapfile-waydroid
   sudo /sbin/swapon -p 5 /swapfile-waydroid
   grep -q swapfile-waydroid /etc/fstab || echo '/swapfile-waydroid none swap sw,pri=5 0 0' | sudo tee -a /etc/fstab
   sudo /sbin/swapon --show
   ```

   The last command should list `/dev/zram0` at priority 100 and `/swapfile-waydroid` at priority 5. The
   `/etc/fstab` line is also in `config/fstab-swap.txt`.

9. **Install the launcher commands and icons.**

   ```
   cd ~/googlebook-waydroid
   mkdir -p ~/.local/bin
   cp bin/waydroid-open bin/waydroid-restart ~/.local/bin/
   chmod +x ~/.local/bin/waydroid-open ~/.local/bin/waydroid-restart
   sudo apt install python3-pil
   python3 -I tools/make-launcher-icons.py
   ```

   The helper writes `waydroid-32.png` and `waydroid-restart-32.png` to `~/.local/share/icons`. It makes them on
   your machine from the icon that the Waydroid package installs, so this repository does not copy Waydroid's
   artwork. My own restart icon had an orange arrow; the helper draws a dark badge with a white arrow instead,
   which is easier to see on Waydroid's orange icon.

   The default Debian `~/.profile` adds `~/.local/bin` to your `PATH` only if the folder existed when the shell
   started, so open a new Linux Terminal window before you use the commands by name.

10. **Add the two panel buttons.** Weston needs absolute paths, so this command fills in your home folder. It
    keeps a backup of your current `~/.config/weston.ini` first:

    ```
    cp -n ~/.config/weston.ini ~/.config/weston.ini.bak
    cat >> ~/.config/weston.ini <<EOF

    [launcher]
    icon=$HOME/.local/share/icons/waydroid-32.png
    path=$HOME/.local/bin/waydroid-open
    displayname=Waydroid

    [launcher]
    icon=$HOME/.local/share/icons/waydroid-restart-32.png
    path=$HOME/.local/bin/waydroid-restart
    displayname=Restart Waydroid
    EOF
    systemctl --user restart weston
    ```

    The result looks like `config/weston-launchers.ini`, with `/home/YOUR_USER` replaced by your home folder.
    Weston reads this file only when it starts, which is why it is restarted. That closes every window on the
    Linux display for a few seconds. Android itself keeps running.

11. **Start Waydroid and turn off auto-freeze.** Open the Linux Terminal's display view and tap the new
    **Waydroid** button on the panel, or run `setsid -f waydroid-open >/dev/null 2>&1` in the Terminal. Wait until
    the Android home screen appears (about 20 seconds). Then, as your normal user and without `sudo`, run:

    ```
    waydroid prop set persist.waydroid.suspend false
    sudo waydroid shell -- getprop persist.waydroid.suspend 2>&1 | cat
    waydroid status
    ```

    The second command should print `false`. If `waydroid status` shows `Container: FROZEN`, unfreeze it once:

    ```
    sudo waydroid container unfreeze
    ```

    You can also check that ARM translation is active. The first command should list `armeabi-v7a` and
    `arm64-v8a`, and the second should print `libhoudini.so`:

    ```
    sudo waydroid shell -- getprop ro.product.cpu.abilist 2>&1 | cat
    sudo waydroid shell -- getprop ro.dalvik.vm.native.bridge 2>&1 | cat
    ```

12. **Register Waydroid with Google.** Google blocks Play sign-in on uncertified Android systems unless the owner
    registers them. Google's official page for this is <https://www.google.com/android/uncertified/>. You sign
    in with your Google account and enter the system's Google Services Framework Android ID, a long decimal
    number. Only you can do this, because it is tied to your account.

    The ID is stored in Waydroid's Google Services Framework database, which exists after Android has booted
    once. This command reads it without changing anything:

    ```
    sudo python3 -I -c "import sqlite3,sys; c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro', uri=True); print(c.execute(\"select value from main where name='android_id'\").fetchone()[0])" ~/.local/share/waydroid/data/data/com.google.android.gsf/databases/gservices.db
    ```

    According to its README, waydroid_script can also print the ID with
    `sudo venv/bin/python3 main.py certified`, run from its folder.

    Copy the number, open <https://www.google.com/android/uncertified/>, sign in with the Google account you will
    use in Waydroid, paste the ID and register it. Keep the ID to yourself: it identifies your Waydroid system to
    Google.

13. **Restart Waydroid and sign in to Google Play.** Tap **Restart Waydroid** on the panel or run
    `setsid -f waydroid-restart >/dev/null 2>&1`. Optionally, clear the Play Store's cache first so it checks the
    registration again:

    ```
    sudo waydroid shell -- sh -c 'am force-stop com.android.vending; pm clear --cache-only com.android.vending' 2>&1 | cat
    ```

    Then open the Play Store in the Waydroid window and sign in with the same account. Registration can take a
    while to take effect. If sign-in still fails, wait, restart Waydroid and try again. Do not clear the data of
    the Google Services Framework app, because that creates a new Android ID that you would have to register
    again.

## Using it

- **To open Waydroid,** open the Linux Terminal's display view and tap the **Waydroid** button on the panel. From
  a terminal, run `waydroid-open`. It keeps running while the window is open, so run it in a separate Terminal
  window or detach it with `setsid -f waydroid-open >/dev/null 2>&1`. If the Waydroid window is already open, the
  command does nothing, so it never stacks a second window. Otherwise it starts the container service with
  `sudo -n systemctl start waydroid-container` and then opens the full Android window, starting the Android
  session if it is not running.
- **To restart Android,** tap **Restart Waydroid**, or run `waydroid-restart`. It closes the Waydroid window, stops
  the Android session, restarts the container service and opens the window again. Android is back after about
  20 seconds. Use it whenever Android freezes or misbehaves.
- **To install apps,** use the Play Store inside the Waydroid window.
- **To check the state,** run `waydroid status`. To see memory and swap use, run `free -h`.
- **To stop Android,** run `waydroid session stop`.

Waydroid runs only while the Linux Terminal's virtual machine runs. When the Googlebook's screen turns off, the
virtual machine can pause until you wake the laptop. My write-up on the Linux Terminal's Keep Awake setting, in
the [smaller fixes](https://github.com/iamflying29-sketch/googlebook-projects/tree/main/smaller-fixes) of the hub
repository, explains what that setting does.

## Updating, and what happens after app or GooglebookOS updates

- **Waydroid package upgrades** (`sudo apt update` and `sudo apt upgrade`) replace `waydroid-net.sh`, which puts
  `LXC_USE_NFT="false"` back. The drop-in fixes the line again the next time `waydroid-container.service`
  starts. After an upgrade, tap **Restart Waydroid** or run `waydroid-restart`, which restarts the service and
  so re-applies the change. You can check it with `grep '^LXC_USE_NFT' /usr/lib/waydroid/data/scripts/waydroid-net.sh`.
- **Android image upgrades** (`sudo waydroid upgrade`) download new system and vendor images. Afterwards, check the
  ABI list again (step 11). If the ARM ABIs are missing, run waydroid_script's libhoudini installation again.
- **GooglebookOS updates** can update the Linux Terminal and its kernel. The nftables setup keeps working whether
  or not a future kernel adds the `CHECKSUM` target. If the Linux Terminal is reset or reinstalled, everything
  inside its virtual machine is gone, including Waydroid, and you need to start again from step 1.
- **Updating these files:** run `git pull` in `~/googlebook-waydroid` and copy the commands to `~/.local/bin`
  again.

## Uninstalling

To remove the launcher buttons and commands, delete the two `[launcher]` sections from `~/.config/weston.ini` (or
put back `~/.config/weston.ini.bak`), then run:

```
rm ~/.local/bin/waydroid-open ~/.local/bin/waydroid-restart
rm ~/.local/share/icons/waydroid-32.png ~/.local/share/icons/waydroid-restart-32.png
systemctl --user restart weston
```

To remove the swap file, delete the `/swapfile-waydroid` line from `/etc/fstab` with a text editor
(`sudo nano /etc/fstab`), then run:

```
sudo /sbin/swapoff /swapfile-waydroid
sudo rm /swapfile-waydroid
```

To remove the nftables drop-in and restore the original network script (Waydroid will then fail to start in this
virtual machine again):

```
sudo rm /etc/systemd/system/waydroid-container.service.d/use-nft.conf
sudo systemctl daemon-reload
sudo cp /usr/lib/waydroid/data/scripts/waydroid-net.sh.orig /usr/lib/waydroid/data/scripts/waydroid-net.sh
```

To remove Waydroid completely, stop it and remove the package. The last command permanently deletes the Android
images and all Android apps and data:

```
waydroid session stop
sudo systemctl stop waydroid-container
sudo apt remove waydroid
sudo rm -rf /var/lib/waydroid ~/.local/share/waydroid
```

## Troubleshooting

- **Android never finishes starting.** Look at the end of Waydroid's log with `sudo tail -40 /var/lib/waydroid/waydroid.log`.
  If it shows the `CHECKSUM` warning and `Failed to setup waydroid-net`, the nftables change is missing. Check
  that `nftables` is installed, that `LXC_USE_NFT` is `"true"`, and that the drop-in is listed by
  `systemctl cat waydroid-container`.
- **No Waydroid window on the Googlebook.** The window appears only on the Linux Terminal's own display, which you
  see in the Terminal's display view. It never appears on the GooglebookOS desktop. If the display view is open
  but the window is missing or blank, run `waydroid-open` again or use **Restart Waydroid**.
- **Android freezes when its window is hidden, or Play Store downloads stop.** Auto-freeze is still on. Repeat
  step 11, and run `sudo waydroid container unfreeze` if `waydroid status` shows `FROZEN`.
- **`waydroid prop set` says the session is stopped.** You ran it with `sudo`, or Android was not running. Run it
  as your normal user while Waydroid is running.
- **Android is extremely slow or seems frozen.** The virtual machine is probably out of memory. Check `free -h`
  and `sudo /sbin/swapon --show`, make sure the swap file is active, and use **Restart Waydroid**.
- **Google Play refuses to sign in, or says the device is not Play Protect certified.** Register the Android ID
  (step 12), restart Waydroid, and try again later if needed. Do not clear the Google Services Framework app's
  data.
- **A file written by `sudo waydroid shell` ends up owned by root.** In my setup, `sudo waydroid shell` changed the
  owner of the file its output was redirected into. Piping the output through `cat`, as the commands above do,
  avoids that.
- **A script that stops Waydroid kills itself.** A broad pattern such as `pkill -f 'waydroid show-full-ui'` also
  matches the shell that runs the command. The launcher commands match only the real process with
  `^/usr/bin/python3 /usr/bin/waydroid show-full-ui`.

## Safety and privacy notes

- Waydroid runs Android in an LXC container inside the Linux Terminal's virtual machine. It cannot reach
  GooglebookOS itself.
- libhoudini is Intel's closed-source ARM translator, and waydroid_script is a third-party tool. Both run with
  root rights inside the virtual machine. Review them before you use them.
- The official Waydroid installer in step 2 runs a script from Waydroid's website as root. If you prefer, download
  it first with `curl -s https://repo.waydro.id -o waydroid-repo.sh`, read it, and then run it with
  `sudo bash waydroid-repo.sh`.
- Your Google Services Framework Android ID identifies your Waydroid system to Google. Do not publish it.
- The launcher commands only start, stop and show Waydroid. They use `sudo -n systemctl` for the container
  service and make no network connections of their own.

## Limitations and known issues

- **GooglebookOS already runs 64-bit ARM apps.** Its own translation handles them, and apps there use the
  Googlebook's graphics hardware, so they run much faster than in Waydroid. Waydroid mainly adds support for
  32-bit ARM apps. Try the Googlebook's own Play Store first, and
  use Waydroid when an app is not offered there.
- **ARM apps are not proven yet.** An app that ships only with 64-bit ARM libraries installed successfully from
  Waydroid's Play Store, but I have not launched and tested any ARM app. A tiny hand-made ARM64 test program was
  picked up by the translator but did not run to completion, probably because it was not a normal Android
  program, so that test proves nothing either way.
- **No GPU acceleration.** The Linux Terminal's virtual GPU offers no 3D support to the virtual machine (it
  reports no virgl and zero capability sets), so Android draws everything in software. Ordinary apps work, but
  3D games will be slow. This cannot be changed from inside the virtual machine.
- **The window appears only inside the Linux Terminal's display view,** which is 1280 by 720 pixels on my
  Googlebook. Waydroid apps do not appear as normal GooglebookOS windows.
- **Memory is tight.** Linux and Android share 3.8 GB of RAM, so heavy apps may struggle even with the swap file.
- **Apps with strict integrity checks usually refuse to run,** for example many banking apps.
- **Waydroid pauses whenever the Linux Terminal's virtual machine pauses,** for example while the Googlebook
  sleeps.

## Files in this repository

| File | Purpose |
|---|---|
| `bin/waydroid-open` | Shows the Waydroid window, starting the container service and Android first if needed. Never opens a second window. |
| `bin/waydroid-restart` | Closes the window, stops the Android session, restarts the container service and opens the window again. |
| `config/use-nft.conf` | The systemd drop-in for `waydroid-container.service` that switches the network script to nftables at every start. |
| `config/waydroid-net-nft.diff` | The one-line change to `/usr/lib/waydroid/data/scripts/waydroid-net.sh`. |
| `config/weston-launchers.ini` | The two `[launcher]` sections for `~/.config/weston.ini`, with a placeholder home folder. |
| `config/fstab-swap.txt` | The `/etc/fstab` line for the 4 GB swap file at priority 5. |
| `tools/make-launcher-icons.py` | Makes the two 32-pixel panel icons from the icon installed by the Waydroid package. |
| `README.md` | This document. |
| `LICENSE` | The MIT License. |
| `.gitignore` | Keeps build outputs, keys, logs and Python caches out of the repository. |

## Related projects

- [Googlebook Projects](https://github.com/iamflying29-sketch/googlebook-projects): the overview of all my
  Googlebook projects, the shared Getting Started guide, and smaller fixes for the Linux Terminal, including the
  Keep Awake explanation and tmux session protection.
- [Continue On workaround](https://github.com/iamflying29-sketch/googlebook-continue-on): another way I bring
  Android apps onto the Googlebook's screen, by mirroring my phone and tablet.

## Disclaimer and license

This is an independent, unofficial project. It is not affiliated with, endorsed by, or sponsored by Google,
Lenovo or any other company named here. All product names belong to their owners. Released under the MIT
License. Copyright (c) 2026 Thomas Liviakis.

Waydroid, LineageOS, libhoudini and waydroid_script are separate projects with their own licenses. This
repository does not include any of their files.
