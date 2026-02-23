# Renew Let's Encrypt for `www.meubusao.com`

This procedure renews TLS certificates and keeps a local backup copy outside Git tracking.

## 1) Prerequisites

- DNS already points `www.meubusao.com` (and optionally `meubusao.com`) to your server.
- Web server serves this repository as webroot.
- `certbot` installed on server.
- This repository deployed on server path (example):
  - `/var/www/meubusaosite`

## 2) Publish a web confirmation file

A verification file is already included in this repo:

- `.well-known/acme-challenge/verification-www-meubusao-com.txt`

Deploy and verify it is public:

```bash
curl -I https://www.meubusao.com/.well-known/acme-challenge/verification-www-meubusao-com.txt
```

Expected: `HTTP/1.1 200 OK`

## 3) Issue / renew certificate on server

Use webroot mode (recommended for static sites):

```bash
sudo certbot certonly \
  --webroot -w /var/www/meubusaosite \
  -d www.meubusao.com -d meubusao.com \
  --agree-tos --email rlocoselli@yahoo.com.br --non-interactive
```

For regular renewal:

```bash
sudo certbot renew
```

Dry-run renewal test:

```bash
sudo certbot renew --dry-run
```

## 4) Reload web server

After renewal, reload your web server:

```bash
sudo systemctl reload nginx
# or
sudo systemctl reload apache2
```

## 5) Save certificates locally in ignored folder

This repository ignores local cert backups using `.gitignore` (`certs-local/`).

Create backup folder and copy certificates (run from your local machine):

```bash
mkdir -p certs-local/www.meubusao.com/$(date +%F)
scp user@YOUR_SERVER:/etc/letsencrypt/live/www.meubusao.com/fullchain.pem certs-local/www.meubusao.com/$(date +%F)/
scp user@YOUR_SERVER:/etc/letsencrypt/live/www.meubusao.com/privkey.pem certs-local/www.meubusao.com/$(date +%F)/
```

Set strict permissions locally:

```bash
chmod 600 certs-local/www.meubusao.com/*/privkey.pem
```

## 6) Validate certificate expiry

```bash
echo | openssl s_client -connect www.meubusao.com:443 -servername www.meubusao.com 2>/dev/null | openssl x509 -noout -dates -issuer -subject
```

## Notes

- Never commit private keys.
- Keep `certs-local/` only as local backup.
- Prefer automated server renewal with system timer (`certbot.timer`).
