# Sistema de Telefonía IP CANTV (VoIP + Facturación)

Prototipo funcional de una central telefónica (PBX) basado en **Asterisk**, con panel de administración web en **Python (Flask)**, base de datos **MariaDB** y despliegue mediante **Docker**.

El sistema permite gestionar abonados, bloquear líneas por deudas, facturar llamadas por segundo, grabar llamadas y ofrece un IVR interactivo.

---

## Características Principales

- **Central Telefónica**: Llamadas entre extensiones SIP (1001, 1002, etc.).
- **Facturación Automática**: Descuento de saldo por segundo/minuto de llamada.
- **Control de Deudas**: Bloqueo automático de líneas y reproducción de audio de advertencia.
- **IVR (Menú *100)**: Consulta de saldo con lectura de voz dinámica y transferencia a soporte técnico.
- **Panel de Administración**: Login seguro, gestión de usuarios, búsqueda, carga desde Excel/CSV, recargas de saldo y ajustes de tarifas.
- **CDR y Grabaciones**: Historial de llamadas con duración, costo y reproductor de audio integrado.
- **Seguridad**: API protegida para comunicación entre Asterisk y el panel.

---

## Tecnologías Utilizadas

| Tecnología              | Uso                              |
|-------------------------|----------------------------------|
| Ubuntu Server           | Sistema Operativo base           |
| Docker & Docker Compose | Despliegue de infraestructura    |
| Asterisk 22             | Motor de telefonía IP            |
| MariaDB                 | Base de datos (usuarios y CDR)   |
| Python 3 / Flask        | Panel web y lógica de negocio    |
| PhpMyAdmin              | Gestión visual de la base de datos |

---

## Requisitos Previos e Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Jose281201/Sistema-VoIP-CANTV.git
cd Sistema-VoIP-CANTV
```

### 2. Levantar la infraestructura con Docker

```bash
docker compose up -d
```

Esto levantará los contenedores de **Asterisk**, **MariaDB** y **PhpMyAdmin** en segundo plano.

### 3. Instalar parches necesarios en Asterisk

**Instalar conector ODBC (base de datos):**

```bash
docker exec -u root -it asterisk_cantv bash -c "apt-get update && apt-get install -y unixodbc odbc-mariadb"
```

**Descargar y copiar los sonidos en español:**

```bash
docker exec -u root -it asterisk_cantv bash -c "apt-get install -y asterisk-core-sounds-es-wav && cp -rn /usr/share/asterisk/sounds/es/* /var/lib/asterisk/sounds/es/"
```

### 4. Configurar el entorno de Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask pymysql werkzeug
```

---

## Cómo Ejecutar el Proyecto

> **Importante:** El panel de Python debe estar encendido todo el tiempo. Es el "cerebro" que le indica a Asterisk quién tiene saldo, quién debe y a qué número transferir en el IVR. Si cierras esta terminal, las llamadas no funcionarán correctamente.

### 1. Activar el entorno virtual

```bash
source venv/bin/activate
```

### 2. Encender el panel web

```bash
python3 app.py
```

Deja esta terminal abierta (no presiones `Ctrl + C`).

### 3. Acceder al Panel de Administración

- URL: `http://<IP_DEL_SERVIDOR>:5000`
- Usuario: `admin`
- Contraseña: `admin`

### 4. Probar las llamadas (Softphones)

1. Configura un Softphone (Zoiper o MicroSIP) con:
   - Usuario: `1001`
   - Contraseña: `1234`
   - Servidor: IP del servidor

2. Configura otro Softphone con el usuario `1002` (misma contraseña).

3. Realiza pruebas:
   - Llama del **1001** al **1002**
   - Marca `*100` para escuchar el menú del IVR

### 5. Acceder a PhpMyAdmin (Opcional)

- URL: `http://<IP_DEL_SERVIDOR>:8080`
- Usuario: `root`
- Contraseña: `root`

---