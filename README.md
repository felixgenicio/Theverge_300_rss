# The Verge RSS Aggregator (300 entries)

## Motivacion

The Verge publica su feed RSS con un maximo de 10 entradas. Si usas un lector RSS que solo comprueba el feed cuando el ordenador esta encendido, es muy facil perder articulos: basta con que el ordenador este apagado unas horas (por trabajo, vacaciones, fin de semana...) para que los nuevos articulos empujen a los anteriores fuera del feed y desaparezcan para siempre.

Este script soluciona el problema ejecutandose en un servidor siempre encendido, consultando el feed de The Verge cada 10 minutos y acumulando hasta **300 entradas** en un RSS local propio. Asi, cuando abres tu lector RSS, todas las entradas publicadas mientras el ordenador estaba apagado siguen estando ahi.

## Como funciona

- `fetch_verge.py` descarga el feed oficial de The Verge (formato Atom)
- Fusiona las entradas nuevas con las ya almacenadas en `entries.json`
- Genera `verge.rss`, un feed RSS 2.0 estandar con hasta 300 entradas ordenadas por fecha
- Se ejecuta periodicamente via cron o systemd timer

## Archivos

| Archivo | Descripcion |
|---|---|
| `fetch_verge.py` | Script principal |
| `entries.json` | Base de datos local (generado automaticamente, no versionado) |
| `verge.rss` | Feed RSS generado listo para servir (no versionado) |
| `fetch_verge.log` | Log de ejecuciones (no versionado) |
| `SETUP.md` | Instrucciones de instalacion (cron, systemd, nginx, Apache) |

## Uso rapido

```bash
python3 fetch_verge.py
```

Para configurar la ejecucion automatica y servir el fichero RSS, consulta [SETUP.md](SETUP.md).

## Requisitos

- Python 3.9+
- Sin dependencias externas (solo biblioteca estandar)
