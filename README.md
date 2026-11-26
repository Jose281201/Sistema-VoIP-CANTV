# Sistema de Telefonía IP CANTV (VoIP + Facturación)

Prototipo funcional de una central telefónica (PBX) basado en Asterisk, con un panel de administración web en Python (Flask), base de datos MariaDB y despliegue mediante Docker. El sistema permite gestionar abonados, bloquear líneas por deudas, facturar llamadas por segundo, grabar llamadas y ofrece un IVR interactivo.

## 🚀 Características Principales
* **Central Telefónica:** Llamadas entre extensiones SIP (1001, 1002, etc.).
* **Facturación Automática:** Descuento de saldo por segundo/minuto de llamada.
* **Control de Deudas:** Bloqueo automático de líneas y reproducción de audio de advertencia.
* **IVR (Menú *100):** Consulta de saldo con lectura de voz dinámica y transferencia a soporte técnico.
* **Panel de Administración:** Login seguro, gestión de usuarios, búsqueda, carga desde Excel/CSV, recargas de saldo y ajustes de tarifas.
* **CDR y Grabaciones:** Historial de llamadas con duración, costo y reproductor de audio integrado.
* **Seguridad:** API protegida para comunicación entre Asterisk y el panel.

## 🛠️ Tecnologías Utilizadas
* **Ubuntu Server** (Sistema Operativo base).
* **Docker & Docker Compose** (Despliegue de infraestructura).
* **Asterisk 22** (Motor de telefonía IP).
* **MariaDB** (Base de datos para usuarios y CDR).
* **Python 3 / Flask** (Panel web y lógica de negocios).
* **PhpMyAdmin** (Gestión visual de la base de datos).

---

## ⚙️ Requisitos Previos e Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd TU_REPOSITORIO