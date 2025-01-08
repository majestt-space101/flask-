import os
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for
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

from folium import Icon

def create_map(filepath):
    # Baca data dari Excel
    data = pd.read_excel(filepath)
    
    # Cetak data untuk debugging
    print("Data dari file Excel:")
    print(data.head())  # Menampilkan 5 baris pertama data di terminal
    
    # Validasi kolom
    required_columns = ['name', 'latitude', 'longitude', 'description', 
                        'penanggung_jawab', 'mulai_pekerjaan', 'volume_scaffolding']
    for col in required_columns:
        if col not in data.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Normalisasi latitude dan longitude jika nilainya terlalu besar
    if data['latitude'].abs().max() > 90 or data['longitude'].abs().max() > 180:
        print("Normalizing latitude and longitude...")
        data['latitude'] = data['latitude'] / 1_000_000
        data['longitude'] = data['longitude'] / 1_000_000
    
    # Pastikan tipe data numerik
    data['latitude'] = data['latitude'].astype(float)
    data['longitude'] = data['longitude'].astype(float)
    
    # Buat peta interaktif
    map_center = [data['latitude'].mean(), data['longitude'].mean()]
    print(f"Map center: {map_center}")  # Debug lokasi pusat peta
    mymap = folium.Map(location=map_center, zoom_start=6)
    
    # Zoom otomatis berdasarkan jarak koordinat
    if len(data) > 1:
        min_lat, max_lat = data['latitude'].min(), data['latitude'].max()
        min_lon, max_lon = data['longitude'].min(), data['longitude'].max()
        bounds = [[min_lat, min_lon], [max_lat, max_lon]]
        mymap.fit_bounds(bounds)

    # Tambahkan marker ke peta dengan warna berdasarkan description
    for _, row in data.iterrows():
        # Tentukan warna berdasarkan isi description
        if "sudah tagging" in row['description'].lower():
            color = "green"
        elif "belum tagging" in row['description'].lower():
            color = "red"
        else:
            color = "blue"  # Default untuk deskripsi lainnya
        
        print(f"Adding marker: {row['name']} at {row['latitude']}, {row['longitude']} with color {color}")
        
        # Tambahkan marker dengan popup yang berisi informasi tambahan
        popup_content = f"""
        <b>{row['name']}</b><br>
        <b>Description:</b> {row['description']}<br>
        <b>Penanggung Jawab:</b> {row['penanggung_jawab']}<br>
        <b>Mulai Pekerjaan:</b> {row['mulai_pekerjaan']}<br>
        <b>Volume Scaffolding:</b> {row['volume_scaffolding']}
        """
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(color=color)
        ).add_to(mymap)
    
    # Simpan peta sebagai file HTML
    output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'map.html')
    mymap.save(output_file)
    print(f"Map saved to {output_file}")


if __name__ == "__main__":
    app.run(debug=True)
