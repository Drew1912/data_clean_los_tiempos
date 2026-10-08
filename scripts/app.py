import os
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from core_processor import DataProcessor

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
REPORTS_FOLDER = 'reports'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/procesar', methods=['POST'])
def procesar_archivos():
    # Check if files were provided
    if 'ventas' not in request.files or 'contabilidad' not in request.files:
        return jsonify({"error": "Debe enviar ambos archivos: 'ventas' y 'contabilidad'"}), 400

    file_ventas = request.files['ventas']
    file_conta = request.files['contabilidad']

    if file_ventas.filename == '' or file_conta.filename == '':
        return jsonify({"error": "Ningún archivo seleccionado"}), 400

    if not (allowed_file(file_ventas.filename) and allowed_file(file_conta.filename)):
        return jsonify({"error": "Tipos de archivo no soportados. Use Excel, CSV o TXT"}), 400

    try:
        # Save files temporarily
        ventas_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file_ventas.filename))
        conta_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file_conta.filename))
        
        file_ventas.save(ventas_path)
        file_conta.save(conta_path)
        
        # Process files
        processor = DataProcessor()
        result = processor.process_files(ventas_path, conta_path)
        
        if result['status'] == 'success':
            return jsonify({
                "message": "Archivos procesados con éxito",
                "resultados": result['stats'],
                "descargar_reporte": f"/api/reportes/{result['report_file']}"
            }), 200
        else:
            return jsonify({"error": "Error al procesar archivos", "detalle": result['message']}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reportes/<filename>', methods=['GET'])
def descargar_reporte(filename):
    try:
        return send_file(os.path.join(REPORTS_FOLDER, secure_filename(filename)), as_attachment=True)
    except Exception as e:
        return jsonify({"error": "Reporte no encontrado"}), 404

if __name__ == '__main__':
    # Running locally for the Phase 1 test
    app.run(debug=True, port=5000)
