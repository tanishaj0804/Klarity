#!/usr/bin/env bash
# One-time setup of the Klarity EC2 server (Ubuntu). Run it ON the server:
#     bash bootstrap_ec2.sh
# It installs Docker, adds swap, gets the repo, creates the secrets file with random
# passwords, starts Oracle XE, MySQL and PostgreSQL, and waits until Oracle is ready.
# Safe to run again: it never overwrites an existing .env file.
#     bash bootstrap_ec2.sh --env-only     # only create the .env file here (used for testing)
set -euo pipefail

REPO_URL="https://github.com/tanishaj0804/Klarity.git"
REPO_DIR="$HOME/Klarity"

pw() { openssl rand -base64 36 | tr -dc 'A-Za-z0-9' | head -c 20; }

write_env() {
  if [ -f .env ]; then
    echo ".env already exists, keeping it."
    return
  fi
  umask 077
  cat > .env <<ENVEOF
MYSQL_ROOT_PASSWORD=$(pw)
MYSQL_DATABASE=crm
MYSQL_USER=klarity_app
MYSQL_PASSWORD=$(pw)
ORACLE_PASSWORD=$(pw)
ORACLE_USER=klarity_app
ORACLE_APP_PASSWORD=$(pw)
PG_DATABASE=catalog
PG_USER=klarity_app
PG_PASSWORD=$(pw)
ENVEOF
  chmod 600 .env
  echo "Created .env with random passwords."
}

if [ "${1:-}" = "--env-only" ]; then
  write_env
  exit 0
fi

echo "== 1/5 packages"
sudo apt-get update -y
sudo apt-get install -y git openssl curl

echo "== 2/5 Docker"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER" || true

echo "== 3/5 swap (a safety net for Oracle)"
if [ "$(swapon --show | wc -l)" -eq 0 ]; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo "== 4/5 repo and secrets"
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR/infra/aws"
write_env

echo "== 5/5 databases"
sudo docker compose up -d
echo "Waiting for Oracle (first start takes a few minutes)..."
for _ in $(seq 1 90); do
  if sudo docker logs klarity-oracle 2>&1 | grep -q "DATABASE IS READY TO USE!"; then
    echo "Oracle is ready."
    break
  fi
  sleep 10
done
sudo docker compose ps
echo
echo "Done. Copy these lines into your laptop's .env.aws (they are shown only for you):"
echo "------------------------------------------------------------"
cat .env
echo "------------------------------------------------------------"
echo "Then clear this screen:  clear"
