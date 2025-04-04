#!/bin/bash

LOG_FILE="/home/gkilburg_biz/git/tempo/lavalink.out"
GITHUB_LAVALINK="https://api.github.com/repos/lavalink-devs/Lavalink/releases/latest"
GITHUB_YTPLUGIN="https://api.github.com/repos/lavalink-devs/youtube-source/releases/latest"

# Get local Lavalink version from bottom of log
lavalink_version=$(grep "Version:" "$LOG_FILE" | tail -n 1 | awk '{print $2}')
echo "Local Lavalink version: $lavalink_version"

# Get latest Lavalink version from GitHub API
latest_lavalink=$(curl -s "$GITHUB_LAVALINK" | grep -oP '"tag_name":\s*"\K[^"]+')
echo "Latest Lavalink version: $latest_lavalink"

# Get local YouTube plugin version from bottom of log
yt_plugin_version=$(grep "Found plugin 'youtube-plugin'" "$LOG_FILE" | tail -n 1 | grep -oP "version \K[\d\.]+")
echo "Local YouTube plugin version: $yt_plugin_version"

# Get latest YouTube plugin version from GitHub API
latest_yt_plugin=$(curl -s "$GITHUB_YTPLUGIN" | grep -oP '"tag_name":\s*"\K[^"]+')
echo "Latest YouTube plugin version: $latest_yt_plugin"

# Clean GitHub tags (remove "v" prefix)
latest_lavalink_clean=${latest_lavalink#v}
latest_yt_plugin_clean=${latest_yt_plugin#v}



# Compare local versions to latest
if ["$lavalink_version" != "$latest_lavalink_clean"]; then
    echo "Lavalink update available."
else
    echo "Lavalink is up to date."
fi

if ["$yt_plugin_version" != "$latest_yt_plugin_clean"]; then
    echo "YouTube plugin update available."
else
    echo "YouTube plugin is up to date."
fi