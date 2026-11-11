# EC2 runbook (klarity-sources)

| Task | Command |
| --- | --- |
| Start server, write new IP into settings | `python scripts/aws_host.py start --env-file .env.aws` |
| Allow this laptop | `python scripts/aws_host.py allow-my-ip --label home` (or `office`) |
| See state, IP, firewall rules | `python scripts/aws_host.py status` |
| Stop (keeps data) | `python scripts/aws_host.py stop` |
| Point scripts at AWS | `$env:KLARITY_ENV_FILE = ".env.aws"` |
| Log in | `ssh -i $HOME\.ssh\klarity-key.pem ubuntu@<IP>` |
| Container state | `cd ~/Klarity/infra/aws; sudo docker compose ps` |
| Oracle log | `sudo docker logs klarity-oracle --tail 50` |

Rules: never open ports to 0.0.0.0/0; stop the server at the end of the day; never commit `.env*` or the key.
Cleanup at the end of the internship: terminate the instance, delete the volume, delete the security group and key pair.
