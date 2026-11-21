#!/usr/bin/env bash
# Run ON the EC2 server. Creates the 'fivetran' OS user that Fivetran's SSH tunnel logs in as.
#   bash ssh_tunnel_user.sh "ssh-rsa AAAA... (the public key from the Fivetran connector form, one line)"
# Why a tunnel: Fivetran requires TLS on direct database connections. Through an SSH tunnel
# the traffic is encrypted by SSH, and only port 22 has to be opened to Fivetran.
set -euo pipefail
KEY="${1:-}"
[ -n "$KEY" ] || { echo "Usage: bash ssh_tunnel_user.sh \"<public key on one line>\""; exit 1; }
getent group fivetran >/dev/null || sudo groupadd fivetran
id fivetran >/dev/null 2>&1 || sudo useradd -m -g fivetran -s /bin/bash fivetran
sudo install -d -m 700 -o fivetran -g fivetran /home/fivetran/.ssh
# Each Fivetran connector shows its own key, so ADD the key (once) instead of replacing the file.
sudo touch /home/fivetran/.ssh/authorized_keys
if ! sudo grep -qxF "$KEY" /home/fivetran/.ssh/authorized_keys; then
  printf '%s\n' "$KEY" | sudo tee -a /home/fivetran/.ssh/authorized_keys >/dev/null
fi
sudo chown fivetran:fivetran /home/fivetran/.ssh/authorized_keys
sudo chmod 600 /home/fivetran/.ssh/authorized_keys
echo "Done. The key was added for user 'fivetran'."
echo "Server private IP (try 127.0.0.1 first as the database host in the Fivetran form, else this):"
hostname -I | awk '{print $1}'
