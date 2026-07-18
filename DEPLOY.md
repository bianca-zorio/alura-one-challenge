# ☁️ Guía de despliegue en Oracle Cloud (OCI) con HTTPS

Guía paso a paso para publicar el **Alura Agente** en una máquina virtual de OCI,
con nginx como proxy inverso y HTTPS gratuito (Let's Encrypt).

Resultado final: `https://tu-dominio` → tu agente corriendo en la nube 🔒

---

## 0. Lo que necesitas
- Cuenta en [Oracle Cloud](https://cloud.oracle.com) (capa *Always Free*).
- Tu clave de Google Gemini (la del `.env` local).
- ~30-40 minutos.

---

## 1. Crear la máquina virtual (VM)

En la consola de OCI: **Menú ☰ → Compute → Instances → Create Instance**.

- **Name:** `alura-agente`
- **Image:** Canonical **Ubuntu 22.04**
- **Shape:** *Change Shape* → **Ampere (ARM)** → `VM.Standard.A1.Flex`
  - **1 OCPU** y **6 GB RAM** (dentro de la capa Always Free). Suficiente para el
    modelo de embeddings.
- **SSH keys:** elige *Generate a key pair for me* y **descarga la llave privada**
  (guárdala bien; la necesitarás para conectarte). O sube tu llave pública si ya
  tienes una.
- Deja el resto por defecto y crea la instancia.

Cuando termine, anota la **Public IP address** (ej. `140.238.x.x`).

---

## 2. Abrir los puertos 80 y 443 en OCI (Security List)

Por defecto OCI solo deja pasar el puerto 22 (SSH). Hay que abrir el 80 y el 443.

**Networking → Virtual Cloud Networks →** (tu VCN) **→ Subnets →** (tu subnet)
**→ Security Lists →** (default) **→ Add Ingress Rules**. Agrega dos reglas:

| Source CIDR | IP Protocol | Destination Port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

---

## 3. Conectarte por SSH

Desde tu PC (PowerShell), usando la llave privada que descargaste:

```powershell
# Ajusta la ruta a tu llave y la IP pública
ssh -i C:\ruta\a\tu-llave.key ubuntu@LA_IP_PUBLICA
```
La primera vez acepta la huella escribiendo `yes`.

> Si da error de permisos de la llave en Windows, muévela a una carpeta tuya y
> quítale la herencia de permisos, o usa `icacls`.

---

## 4. Abrir los puertos también en el firewall de la VM (¡trampa de OCI!)

Las imágenes de Ubuntu en OCI traen un firewall local (iptables) que **también**
bloquea el 80/443. Hay que abrirlos por dentro:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## 5. Instalar dependencias del sistema

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip git nginx
```

---

## 6. Clonar el proyecto e instalar

```bash
cd ~
git clone https://github.com/bianca-zorio/alura-one-challenge.git
cd alura-one-challenge
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

---

## 7. Crear el archivo `.env` con tu clave

```bash
nano .env
```
Pega esto (con tu clave real) y guarda con `Ctrl+O`, `Enter`, `Ctrl+X`:
```
GOOGLE_API_KEY=TU_CLAVE_DE_GEMINI
GOOGLE_MODEL=gemini-flash-latest
```

---

## 8. Construir el índice de documentos (una vez)

```bash
.venv/bin/python -m app.ingest
```
Descarga el modelo de embeddings y crea el índice. Tarda un par de minutos.

**Prueba rápida** de que arranca (Ctrl+C para detener tras ver que responde):
```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 9. Convertir la app en un servicio permanente (systemd)

Copia el archivo de servicio incluido en el repo y actívalo:
```bash
sudo cp deploy/alura-agente.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now alura-agente
sudo systemctl status alura-agente     # debe decir "active (running)"
```
Ahora tu app corre sola en segundo plano y arranca con la VM.

---

## 10. Dominio gratuito con DuckDNS (para el HTTPS)

El HTTPS necesita un dominio. Si no tienes uno, usa **DuckDNS** (gratis):
1. Entra a [duckdns.org](https://www.duckdns.org) e inicia sesión (Google/GitHub).
2. Crea un subdominio, por ejemplo `bianca-alura` → te dará `bianca-alura.duckdns.org`.
3. En el campo **current ip**, pon la **IP pública de tu VM** y pulsa *update ip*.

---

## 11. Configurar nginx

```bash
sudo cp deploy/nginx-alura-agente.conf /etc/nginx/sites-available/alura-agente
sudo nano /etc/nginx/sites-available/alura-agente     # reemplaza TU_DOMINIO por bianca-alura.duckdns.org
sudo ln -s /etc/nginx/sites-available/alura-agente /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t          # comprueba la sintaxis
sudo systemctl restart nginx
```
Prueba en el navegador: `http://bianca-alura.duckdns.org` (aún sin candado).

---

## 12. Activar HTTPS con Let's Encrypt (Certbot)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d bianca-alura.duckdns.org
```
Responde el correo y acepta. Certbot obtiene el certificado, edita nginx para el
puerto 443 y activa la redirección de HTTP a HTTPS automáticamente.

¡Listo! Abre **https://bianca-alura.duckdns.org** → tu agente con candado 🔒

---

## 13. Evidencia para el README

- **Enlace público:** tu URL `https://...duckdns.org`
- **Captura:** toma una foto de la app respondiendo una pregunta y agrégala.

Comandos útiles de mantenimiento:
```bash
sudo systemctl restart alura-agente     # reiniciar la app
sudo journalctl -u alura-agente -f       # ver los logs en vivo
```
