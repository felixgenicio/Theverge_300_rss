# Verge RSS Aggregator - Configuración

Script que obtiene el RSS de The Verge cada 10 minutos y genera un fichero RSS local con las últimas 300 entradas.

## Ficheros

| Fichero | Descripción |
|---|---|
| `fetch_verge.py` | Script principal |
| `entries.json` | Base de datos local de entradas (se crea automáticamente) |
| `verge.rss` | RSS generado listo para servir |
| `fetch_verge.log` | Log de ejecuciones |

## Ejecución manual

```bash
python3 /path/to/verge_rss/fetch_verge.py
```

## Programar la ejecución cada 10 minutos

### Opción A: cron

```bash
crontab -e
```

Añade:

```
*/10 * * * * /usr/bin/python3 /path/to/verge_rss/fetch_verge.py
```

### Opción B: systemd timer (recomendado)

Crea `/etc/systemd/system/verge-rss.service`:

```ini
[Unit]
Description=Fetch The Verge RSS

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /path/to/verge_rss/fetch_verge.py
User=YOUR_USER
```

Crea `/etc/systemd/system/verge-rss.timer`:

```ini
[Unit]
Description=Run verge-rss every 10 minutes

[Timer]
OnBootSec=1min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
```

Activa el timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now verge-rss.timer
```

Comprueba el estado:

```bash
systemctl status verge-rss.timer
journalctl -u verge-rss.service -f
```

## Servir el fichero RSS

### nginx

```nginx
location /verge.rss {
    alias /path/to/verge_rss/verge.rss;
    types { application/rss+xml rss; }
}
```

### Apache

```apache
Alias /verge.rss /path/to/verge_rss/verge.rss
<Files "verge.rss">
    ForceType application/rss+xml
</Files>
```

Apunta tu lector RSS a `http://tu-servidor/verge.rss`.
