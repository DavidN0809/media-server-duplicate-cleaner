from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import json
import os
import threading
from datetime import datetime

app = Flask(__name__)

process_status = {
    'running': False,
    'output': [],
    'error': None
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    config_file = 'config.json'
    
    if request.method == 'GET':
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({
            'sonarr': {'url': '', 'api_key': ''},
            'radarr': {'url': '', 'api_key': ''}
        })
    
    elif request.method == 'POST':
        config_data = request.json
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        return jsonify({'success': True, 'message': 'Configuration saved'})

@app.route('/api/protected-dirs', methods=['GET', 'POST'])
def handle_protected_dirs():
    protected_file = 'protected_dirs.json'
    
    if request.method == 'GET':
        if os.path.exists(protected_file):
            with open(protected_file, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({'protected_dirs': []})
    
    elif request.method == 'POST':
        protected_data = request.json
        with open(protected_file, 'w') as f:
            json.dump(protected_data, f, indent=4)
        return jsonify({'success': True, 'message': 'Protected directories saved'})

@app.route('/api/env', methods=['GET', 'POST'])
def handle_env():
    env_file = '.env'
    
    if request.method == 'GET':
        env_data = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_data[key] = value
        return jsonify(env_data)
    
    elif request.method == 'POST':
        env_data = request.json
        with open(env_file, 'w') as f:
            for key, value in env_data.items():
                f.write(f'{key}={value}\n')
        return jsonify({'success': True, 'message': 'Environment variables saved'})

@app.route('/api/run', methods=['POST'])
def run_script():
    global process_status
    
    if process_status['running']:
        return jsonify({'success': False, 'message': 'A process is already running'}), 400
    
    data = request.json
    script_type = data.get('script_type', 'full')
    options = data.get('options', {})
    
    cmd = ['bash', './media_cleanup.sh']
    
    if script_type == 'find_only':
        cmd.append('--find-only')
    elif script_type == 'cleanup_only':
        cmd.append('--cleanup-only')
    
    if options.get('dry_run'):
        cmd.append('--dry-run')
    
    if options.get('auto'):
        cmd.append('--auto')
    
    if options.get('filter'):
        cmd.append(f'--filter={options["filter"]}')
    
    if options.get('min_size'):
        cmd.append(f'--min-size={options["min_size"]}')
    
    if options.get('max_size'):
        cmd.append(f'--max-size={options["max_size"]}')
    
    def run_process():
        global process_status
        process_status['running'] = True
        process_status['output'] = []
        process_status['error'] = None
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                process_status['output'].append({
                    'timestamp': datetime.now().isoformat(),
                    'line': line.rstrip()
                })
            
            process.wait()
            
            if process.returncode != 0:
                process_status['error'] = f'Process exited with code {process.returncode}'
        
        except Exception as e:
            process_status['error'] = str(e)
        
        finally:
            process_status['running'] = False
    
    thread = threading.Thread(target=run_process)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Process started'})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(process_status)

@app.route('/api/reports', methods=['GET'])
def list_reports():
    reports = []
    for file in os.listdir('.'):
        if file.endswith('_report.json') or file.endswith('_duplicates.json'):
            reports.append({
                'name': file,
                'size': os.path.getsize(file),
                'modified': datetime.fromtimestamp(os.path.getmtime(file)).isoformat()
            })
    return jsonify(reports)

@app.route('/api/reports/<filename>', methods=['GET'])
def get_report(filename):
    if not (filename.endswith('_report.json') or filename.endswith('_duplicates.json')):
        return jsonify({'error': 'Invalid file type'}), 400
    
    if not os.path.exists(filename):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filename, mimetype='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
