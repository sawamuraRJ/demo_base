from flask import Flask, render_template, redirect, url_for, request
from mysql import connector
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde .env
load_dotenv()
app = Flask(__name__)

# Configuración de la base de datos
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT'))
}

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/crear_concepto', methods=['GET', 'POST'])
def crear_concepto():
    mensaje = None
    if request.method == 'POST':
        datos = (
            request.form['concepto'],
            request.form['nombre'],
            float(request.form['monto']),
            request.form.get('fecha') or None,
            request.form['tipo'],
            int(request.form['id_semestre']),
            int(request.form['id_penalidad'])
        )
        conn = connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.callproc('pago_academico', datos)
        conn.commit()
        cursor.execute("SELECT LAST_INSERT_ID();")
        nuevo_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        mensaje = "Concepto creado correctamente."
        return redirect(url_for('registrar_pago', id_pago_academico=nuevo_id))

    return render_template('crear_concepto.html', mensaje=mensaje)


@app.route('/registrar_pago', methods=['GET', 'POST'])
def registrar_pago():
    mensaje = None
    conn = None
    cursor = None
    id_pago_academico = request.args.get('id_pago_academico') or request.form.get('id_pago_academico')
    concepto = None

    try:
        if id_pago_academico:
            conn = connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT concepto FROM Pago_Academico WHERE idPago_Academico = %s", (id_pago_academico,))
            resultado = cursor.fetchone()
            concepto = resultado[0] if resultado else "Desconocido"

        if request.method == 'POST':
            cubierto = 1 if request.form.get('cubierto') == '1' else 0
            aplica_penalidad = 1 if request.form.get('aplica_penalidad') == '1' else 0
            fecha_str = request.form.get('fecha', '')
            fecha = fecha_str if fecha_str else None
            datos = (
                fecha,
                request.form['hora'],
                float(request.form['monto_pagado']),
                request.form['medio_pago'],
                request.form['nro_operacion'],
                cubierto,
                int(request.form['id_descuento']),
                aplica_penalidad,
                int(id_pago_academico)
            )
            cursor.callproc('pago_detalle', datos)
            result = list(cursor.stored_results())
            nuevo_id = result[0].fetchone()[0] if result else None
            mensaje = f"Pago registrado con ID: {nuevo_id}" if nuevo_id else "Pago registrado."
            conn.commit()

    except Exception as e:
        mensaje = f"Error al registrar pago: {e}"

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return render_template('registrar_pago.html',
                           mensaje=mensaje,
                           id_pago_academico=id_pago_academico,
                           concepto=concepto)


@app.route('/registro_estudiante', methods=['GET', 'POST'])
def registro_estudiante():
    mensaje = ""
    if request.method == 'POST':
        dni = request.form['dni']
        nombre = request.form['nombre']
        apellido_paterno = request.form['apellido_paterno']
        apellido_materno = request.form['apellido_materno']
        correo = request.form['correo']
        carrera = request.form['carrera']
        pago = request.form['pago']

        conn = connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.callproc('sp_insertar_estudiante', [
            dni, nombre, apellido_paterno, apellido_materno, correo, carrera, pago
        ])
        conn.commit()
        cursor.close()
        conn.close()
        mensaje = "Estudiante registrado exitosamente"

    return render_template('registro_estudiante.html', mensaje=mensaje)


@app.route('/baucher', methods=['GET', 'POST'])
def baucher():
    pagos = []
    if request.method == 'POST':
        dni = request.form['dni']  # <-- extraer DNI
        conn = connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_generar_baucher', [dni])  # <-- pasar DNI al SP
        for result in cursor.stored_results():
            pagos.extend(result.fetchall())
        cursor.close()
        conn.close()
    return render_template('baucher.html', datos=pagos)  


if __name__ == '__main__':
    app.run(debug=True)
