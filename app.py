from flask import Flask, render_template_string, request, session, redirect, url_for
from datetime import timedelta
import os
import csv
import io
import pymysql

app = Flask(__name__)
app.secret_key = os.environ.get('CANTV_SECRET', 'clave_secreta_cantv_2026')

# ==================== PARÁMETROS DEL SISTEMA ====================
SESSION_MINUTOS = 1            # duración de la sesión del panel (minutos)
TARIFA_POR_DEFECTO = 0.015     # Bs por segundo (0.90 Bs/minuto)
LIMITE_MAX_COBRO = 3600        # tope de seguridad: nunca cobrar más de 1 hora

app.permanent_session_lifetime = timedelta(minutes=SESSION_MINUTOS)

# ==================== BASE DE DATOS ====================
def get_db():
    return pymysql.connect(
        host="127.0.0.1",
        user="cantv_user",
        password="cantv_pass",
        database="cantv_db",
        charset="utf8mb4",
    )

def solo_digitos(texto):
    return ''.join(c for c in str(texto if texto is not None else '') if c.isdigit())

def get_config(clave, defecto):
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT valor FROM configuracion WHERE clave=%s", (clave,))
                fila = cur.fetchone()
        finally:
            conn.close()
        if fila and fila[0] not in (None, ''):
            return fila[0]
        return defecto
    except Exception as e:
        print("Advertencia en get_config (puede que la tabla no exista):", e)
        return defecto

def set_config(clave, valor):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM configuracion WHERE clave=%s", (clave,))
            existe = cur.fetchone()[0] > 0
            if existe:
                cur.execute("UPDATE configuracion SET valor=%s WHERE clave=%s", (valor, clave))
            else:
                cur.execute("INSERT INTO configuracion (clave, valor) VALUES (%s, %s)", (clave, valor))
        conn.commit()
    finally:
        conn.close()

def get_tarifa():
    try:
        t = float(get_config('tarifa_seg', TARIFA_POR_DEFECTO))
        return t if t > 0 else TARIFA_POR_DEFECTO
    except (TypeError, ValueError):
        return TARIFA_POR_DEFECTO

# --- HTML DE LA PANTALLA DE LOGIN ---
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Panel CANTV</title>
    <style>
        body { font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #f4f4f9; margin: 0; }
        .login-box { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; width: 300px;}
        .logo-container { margin-bottom: 20px; }
        .logo-cantv { width: 180px; height: auto; }
        h2 { color: #0056b3; margin-bottom: 20px;}
        input { padding: 10px; margin: 10px 0; width: 90%; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 20px; background: #0056b3; color: white; border: none; border-radius: 4px; cursor: pointer; width: 95%; font-size: 16px; font-weight: bold;}
        button:hover { background: #004494; }
        .error { color: red; margin-top: 10px; font-size: 14px;}
    </style>
</head>
<body>
    <div class="login-box">
        <div class="logo-container">
            <img src="/static/logo.png" alt="Logo CANTV" class="logo-cantv">
        </div>
        <h2>Iniciar Sesión</h2>
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Usuario" required><br>
            <input type="password" name="password" placeholder="Contraseña" required><br>
            <button type="submit">Ingresar</button>
        </form>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
    </div>
</body>
</html>
"""

# --- HTML DEL PANEL PRINCIPAL ---
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Panel CANTV</title>
    <style>
        body { font-family: Arial; margin: 40px; background-color: #f4f4f9; color: #333; }
        h1, h2 { color: #0056b3; text-align: center; }
        table { border-collapse: collapse; width: 100%; background: white; margin-bottom: 30px;}
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #0056b3; color: white; }
        .btn { padding: 6px 10px; text-decoration: none; color: white; border-radius: 4px; font-weight: bold; font-size: 13px; cursor:pointer;}
        .bloquear { background: #dc3545; }
        .desbloquear { background: #28a745; }
        .recargar { background: #17a2b8; margin-left: 5px; }
        .eliminar { background: #6c757d; margin-left: 5px; }
        .form-section { background: white; padding: 20px; width: 80%; margin: 0 auto 30px auto; border: 1px solid #ddd; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 15px;}
        input[type="text"], input[type="password"], input[type="file"], input[type="number"] { padding: 8px; margin-right: 10px; }
        button { padding: 9px 15px; background: #0056b3; color: white; border: none; border-radius: 4px; cursor: pointer;}
        .header-container { text-align: center; margin-bottom: 20px; position: relative;}
        .logo-cantv { width: 200px; height: auto; }
        .saldo-rojo { color: red; font-weight: bold; }
        .saldo-verde { color: green; font-weight: bold; }
        .logout-btn { position: absolute; top: 10px; right: 10px; background: #dc3545; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-size: 12px; font-weight: bold;}
        .logout-btn:hover { background: #c82333; }
        .tarifa-badge { background: #e9f2ff; border: 1px solid #b6d4ff; color: #0056b3; padding: 6px 12px; border-radius: 4px; display: inline-block; font-size: 13px; margin-bottom: 10px;}
    </style>
</head>
<body>
    <div class="header-container">
        <a href="/logout" class="logout-btn">Cerrar Sesión</a>
        <img src="/static/logo.png" alt="Logo CANTV" class="logo-cantv">
        <h1>Panel de Administración CANTV</h1>
        <div class="tarifa-badge">Tarifa vigente: <b>{{ "%.3f"|format(tarifa) }} Bs/segundo</b> &nbsp;({{ "%.2f"|format(tarifa * 60) }} Bs/minuto)</div>
    </div>

    <div class="form-section">
        <div>
            <h3>Agregar Abonado</h3>
            <form action="/add" method="POST">
                <input type="text" name="extension" placeholder="Extensión" required>
                <input type="text" name="nombre" placeholder="Nombre" required>
                <button type="submit">Agregar</button>
            </form>
        </div>
        <div>
            <h3>Cargar desde Excel/CSV</h3>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <input type="file" name="file" accept=".csv" required>
                <button type="submit">Subir Archivo</button>
            </form>
        </div>
        <div>
            <h3>Configuración de Técnico</h3>
            <form action="/config_tecnico" method="POST">
                <input type="text" name="tecnico" value="{{ tecnico }}" placeholder="Ext Técnico (Ej: 1002)" required>
                <button type="submit">Guardar</button>
            </form>
        </div>
        <div>
            <h3>Tarifa de llamadas</h3>
            <form action="/config_tarifa" method="POST">
                <input type="text" name="tarifa" value="{{ '%.3f'|format(tarifa) }}" placeholder="Bs por segundo" required style="width: 120px;">
                <button type="submit">Guardar</button>
            </form>
        </div>
    </div>

    <h2>Control de Abonados</h2>
    <form method="GET" action="/" style="margin-bottom: 15px; text-align: center;">
        <input type="text" name="search" placeholder="Buscar por nombre o extensión..." value="{{ search_query }}" style="width: 300px;">
        <button type="submit">Buscar</button>
        <a href="/" style="margin-left: 10px; font-size: 14px;">Limpiar</a>
    </form>

    <table>
        <tr>
            <th>Extensión</th><th>Nombre</th><th>Saldo</th><th>Tiempo disponible</th><th>Estado</th><th>Acciones</th>
        </tr>
        {% for user in users %}
        <tr>
            <td>{{ user['extension'] }}</td>
            <td>{{ user['nombre'] }}</td>
            <td class="{% if user['saldo'] <= 0 or user['deuda'] %}saldo-rojo{% else %}saldo-verde{% endif %}">
                {{ "%.2f"|format(user['saldo']) }} Bs
            </td>
            <td>
                {% if user['deuda'] or user['saldo'] <= 0 %}-{% else %}
                    {% set seg = (user['saldo'] / tarifa)|int %}
                    {{ (seg // 60) }} min {{ (seg % 60) }} s
                {% endif %}
            </td>
            <td>
                {% if user['deuda'] %} <span style="color:red; font-weight:bold;">BLOQUEADO (deuda)</span>
                {% elif user['saldo'] <= 0 %} <span style="color:red; font-weight:bold;">BLOQUEADO (sin saldo)</span>
                {% else %} <span style="color:green; font-weight:bold;">Activo</span> {% endif %}
            </td>
            <td>
                <a href="/toggle/{{ user['extension'] }}" class="btn {% if user['deuda'] %}desbloquear{% else %}bloquear{% endif %}">
                    {% if user['deuda'] %}Quitar Deuda{% else %}Bloquear{% endif %}
                </a>
                <a href="/recharge/{{ user['extension'] }}" class="btn recargar">Recargar</a>
                <a href="/delete/{{ user['extension'] }}" class="btn eliminar" onclick="return confirm('¿Seguro que deseas eliminar este abonado?');">Eliminar</a>
            </td>
        </tr>
        {% endfor %}
    </table>
    <br>
    <h2>Historial de Llamadas (CDR)</h2>
    <table>
        <tr>
            <th>Fecha</th><th>Origen</th><th>Destino</th><th>Tiempo</th><th>Estado</th><th>Costo</th><th>Grabación</th>
        </tr>
        {% for call in calls %}
        <tr>
            <td>{{ call['calldate'] }}</td>
            <td>{{ call['src'] }}</td>
            <td>{{ call['dst'] }}</td>
            <td>{{ call['billsec'] }} seg</td>
            <td>{{ call['disposition'] }}</td>
            <td>{{ "%.2f"|format(call['billsec'] * tarifa) }} Bs</td>
            <td>
                {% if call['recordingfile'] %}
                    <audio controls style="height: 25px; width: 150px;">
                        <source src="/static/recordings/{{ call['recordingfile'] }}" type="audio/wav">
                    </audio>
                {% else %}-{% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>

    <script>
        const INACTIVITY_TIME = {{ session_minutos }} * 60 * 1000;
        let inactivityTimer;

        function logoutPorInactividad() {
            window.location.href = "/logout";
        }

        function resetTimer() {
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(logoutPorInactividad, INACTIVITY_TIME);
        }

        ['mousemove', 'mousedown', 'keypress', 'scroll', 'touchstart', 'click'].forEach(function(evento) {
            document.addEventListener(evento, resetTimer, true);
        });

        window.addEventListener('pageshow', function(event) {
            if (event.persisted || (window.performance && window.performance.navigation.type === 1)) {
                window.location.href = "/logout";
            }
        });

        resetTimer();
    </script>
</body>
</html>
"""

# --- CONTROL DE ACCESO ---
@app.before_request
def require_login():
    if request.endpoint and request.endpoint not in ['login', 'static'] and 'logged_in' not in session:
        if not request.path.startswith('/api/'):
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '')
        pw = request.form.get('password', '')
        if user == 'admin' and pw == 'admin':
            session.permanent = True
            session['logged_in'] = True
            return redirect(url_for('index'))
        return render_template_string(LOGIN_HTML, error="Usuario o contraseña incorrectos")
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- RUTAS DEL PANEL ---
@app.route('/')
def index():
    search_query = request.args.get('search', '')
    tarifa = get_tarifa()
    conn = get_db()
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        if search_query:
            sql = "SELECT extension, nombre, deuda, saldo FROM abonados WHERE extension LIKE %s OR nombre LIKE %s"
            cursor.execute(sql, ('%' + search_query + '%', '%' + search_query + '%'))
        else:
            cursor.execute("SELECT extension, nombre, deuda, saldo FROM abonados")
        users = cursor.fetchall()

        cursor.execute("SELECT calldate, src, dst, billsec, disposition, recordingfile FROM cdr ORDER BY id DESC LIMIT 20")
        calls = cursor.fetchall()
    finally:
        conn.close()

    # ¡ESTA ES LA SOLUCIÓN AL ERROR 500! Convertimos los Decimales de MySQL a Float
    for user in users:
        user['saldo'] = float(user['saldo'])

    tecnico = solo_digitos(get_config('tecnico_ext', '1002'))
    if not tecnico:
        tecnico = '1002'

    return render_template_string(
        HTML,
        users=users,
        calls=calls,
        search_query=search_query,
        tecnico=tecnico,
        tarifa=tarifa,
        session_minutos=SESSION_MINUTOS,
    )

@app.route('/delete/<ext>')
def delete_user(ext):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM abonados WHERE extension = %s", (ext,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/config_tecnico', methods=['POST'])
def config_tecnico():
    nuevo_tecnico = solo_digitos(request.form.get('tecnico', ''))
    if len(nuevo_tecnico) >= 3:
        set_config('tecnico_ext', nuevo_tecnico)
    return redirect(url_for('index'))

@app.route('/config_tarifa', methods=['POST'])
def config_tarifa():
    valor = request.form.get('tarifa', '').replace(',', '.').strip()
    try:
        t = float(valor)
        if t > 0:
            set_config('tarifa_seg', f"{t:.4f}")
    except ValueError:
        pass
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    if file and file.filename.endswith('.csv'):
        stream = io.StringIO(file.stream.read().decode("UTF8", errors="replace"), newline=None)
        csv_input = csv.reader(stream)
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                next(csv_input, None) 
                for row in csv_input:
                    if len(row) >= 2:
                        ext = solo_digitos(row[0])
                        nombre = row[1].strip()
                        if not ext or not nombre:
                            continue
                        try:
                            cursor.execute(
                                "INSERT INTO abonados (extension, nombre, deuda, saldo) VALUES (%s, %s, FALSE, 5.00)",
                                (ext, nombre),
                            )
                        except Exception as e:
                            print(f"Error insertando {ext}: {e}")
            conn.commit()
        finally:
            conn.close()
    return redirect(url_for('index'))

@app.route('/toggle/<ext>')
def toggle(ext):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT deuda FROM abonados WHERE extension = %s", (ext,))
            result = cursor.fetchone()
            if result:
                if not result[0]:
                    cursor.execute("UPDATE abonados SET deuda = TRUE, saldo = 0.00 WHERE extension = %s", (ext,))
                else:
                    cursor.execute("UPDATE abonados SET deuda = FALSE WHERE extension = %s", (ext,))
            conn.commit()
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/recharge/<ext>')
def recharge(ext):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE abonados SET saldo = saldo + 5.00, deuda = FALSE WHERE extension = %s", (ext,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/add', methods=['POST'])
def add_user():
    ext = solo_digitos(request.form.get('extension', ''))
    nombre = request.form.get('nombre', '').strip()
    if ext and nombre:
        conn = get_db()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(
                        "INSERT INTO abonados (extension, nombre, deuda, saldo) VALUES (%s, %s, FALSE, 0.00)",
                        (ext, nombre),
                    )
                    conn.commit()
                except Exception as e:
                    print("Error al agregar:", e)
        finally:
            conn.close()
    return redirect(url_for('index'))

# ==================== APIs PARA ASTERISK ====================

@app.route('/api/check/<ext>')
def check_debt(ext):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT deuda, saldo FROM abonados WHERE extension = %s", (ext,))
            result = cursor.fetchone()
    finally:
        conn.close()
    if result:
        deuda = bool(result[0])
        saldo = float(result[1] or 0)
        if deuda or saldo <= 0:
            return "deudor"
    return "activo"

@app.route('/api/balance/<ext>')
def get_balance(ext):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT saldo FROM abonados WHERE extension = %s", (ext,))
            result = cursor.fetchone()
    finally:
        conn.close()
    if result and result[0] is not None:
        saldo = max(float(result[0]), 0.0)
        entero = int(saldo)
        decimales = int(round((saldo - entero) * 100))
        return f"{entero},{decimales}"
    return "0,0"

@app.route('/api/maxtime/<ext>')
def get_maxtime(ext):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT deuda, saldo FROM abonados WHERE extension = %s", (ext,))
            result = cursor.fetchone()
    finally:
        conn.close()

    if not result:
        return "600"

    deuda = bool(result[0])
    saldo = float(result[1] or 0)
    if deuda or saldo <= 0:
        return "bloqueado"

    segundos = int(saldo / get_tarifa())
    return str(segundos) if segundos > 0 else "bloqueado"

@app.route('/api/charge/<ext>/<int:seg>')
def charge_call(ext, seg):
    seg = max(0, min(seg, LIMITE_MAX_COBRO))
    tarifa = get_tarifa()
    costo = round(seg * tarifa, 2)

    conn = get_db()
    nuevo_saldo = None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT saldo FROM abonados WHERE extension = %s", (ext,))
            result = cursor.fetchone()
            if result:
                saldo_actual = float(result[0] or 0)
                nuevo_saldo = round(max(saldo_actual - costo, 0.0), 2)
                if nuevo_saldo < tarifa:
                    nuevo_saldo = 0.0
                cursor.execute("UPDATE abonados SET saldo = %s WHERE extension = %s", (nuevo_saldo, ext))
        conn.commit()
    finally:
        conn.close()

    if nuevo_saldo is None:
        return "activo"
    if nuevo_saldo <= 0:
        return "deudor"
    return f"{nuevo_saldo:.2f}"

@app.route('/api/tecnico')
def get_tecnico():
    valor = solo_digitos(get_config('tecnico_ext', '1002'))
    return valor if valor else "1002"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)