from flask import Flask, request, render_template, redirect, url_for, send_file
import os
import pandas as pd
import folium

app = Flask(__name__)

# Folder untuk menyimpan file yang diupload
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'static/maps'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# Pastikan folder tersedia
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Cek apakah file diupload
        if 'file' not in request.files:
            return "No file part", 400
        
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        
        # Simpan file yang diupload
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Proses file Excel dan buat peta
        try:
            create_map(filepath)
            return redirect(url_for('map'))
        except ValueError as ve:
            return f"Error in data: {ve}", 400
        except Exception as e:
            return f"An unexpected error occurred: {e}", 500
    
    return render_template('index.html')

@app.route('/map')
def map():
    # Akses file peta terakhir
    map_file = os.path.join(app.config['OUTPUT_FOLDER'], 'map.html')
    return render_template('map.html', map_file=map_file)

@app.route('/download-map')
def download_map():
    # Kirim file sebagai unduhan
    map_file = os.path.join(app.config['OUTPUT_FOLDER'], 'map.html')
    return send_file(
        map_file,
        as_attachment=True,
        download_name='generated_map.html'
    )

def create_map(filepath):
    # Baca data dari Excel
    data = pd.read_excel(filepath)
    
    # Validasi kolom
    required_columns = ['name', 'latitude', 'longitude', 'description', 
                        'penanggung_jawab', 'mulai_pekerjaan', 'volume_scaffolding', 
                        'tanggal_spk', 'group', 'progress', 'area']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Normalisasi latitude dan longitude jika nilainya terlalu besar
    if data['latitude'].abs().max() > 90 or data['longitude'].abs().max() > 180:
        data['latitude'] = data['latitude'] / 1_000_000
        data['longitude'] = data['longitude'] / 1_000_000
    
    # Pastikan tipe data numerik
    data['latitude'] = data['latitude'].astype(float)
    data['longitude'] = data['longitude'].astype(float)
    
    # Buat peta interaktif
    map_center = [data['latitude'].mean(), data['longitude'].mean()]
    mymap = folium.Map(location=map_center, zoom_start=6)

    for _, row in data.iterrows():
        # Tentukan warna berdasarkan isi description
        if "sudah tagging" in row['description'].lower():
            color = "green"
        elif "belum tagging" in row['description'].lower():
            color = "red"
        else:
            color = "blue"
        
        # Tambahkan marker dengan popup yang berisi informasi tambahan
        popup_content = f"""
        <b>{row['name']}</b><br>
        <b>Description:</b> {row['description']}<br>
        <b>Penanggung Jawab:</b> {row['penanggung_jawab']}<br>
        <b>Mulai Pekerjaan:</b> {row['mulai_pekerjaan']}<br>
        <b>Volume Scaffolding:</b> {row['volume_scaffolding']}<br>
        <b>Tanggal SPK:</b> {row['tanggal_spk']}<br>
        <b>Group:</b> {row['group']}<br>
        <b>Progress:</b> {row['progress']}<br>
        <b>Area:</b> {row['area']}
        """
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color=color)
        ).add_to(mymap)
    
    # Simpan peta sebagai file HTML
    output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'map.html')
    mymap.save(output_file)


if __name__ == "__main__":
    app.run(debug=True)
