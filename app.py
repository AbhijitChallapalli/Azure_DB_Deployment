from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import pyodbc
import redis
import os
import time
import hashlib
import io
from dotenv import load_dotenv

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'supersecret'  # for flash messages

# Load environment variables
load_dotenv()
password = os.getenv('SQL_PASSWORD')

# SQL Server configuration
server = 'tcp:dbdemo-server.database.windows.net'
database = 'mydb'
username = 'abhi@dbdemo-server'
driver = '{ODBC Driver 18 for SQL Server}'

# Redis configuration
redis_client = redis.StrictRedis(
    host=os.getenv('REDIS_HOST'),
    port=6380,
    db=0,
    password=os.getenv('REDIS_KEY'),
    ssl=True
)
#print("REDIS HOST:", os.getenv("REDIS_HOST"))


# SQL connection
def get_connection():
    return pyodbc.connect(
        f'DRIVER={driver};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
        f'Encrypt=yes;'
        f'TrustServerCertificate=no;'
        f'Connection Timeout=30;'
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    if request.method == 'POST':
        quake_id = request.form['id']
        time_val = request.form['time']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        depth = request.form['depth']
        mag = request.form['mag']
        place = request.form['place']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Earthquakes (id, time, latitude, longitude, depth, mag, place)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, quake_id, time_val, latitude, longitude, depth, mag, place)
        conn.commit()
        cursor.close()
        conn.close()
        flash('Earthquake record inserted successfully!')
        return redirect(url_for('index'))
    return render_template('insert.html')

@app.route('/query', methods=['GET', 'POST'])
def query():
    if request.method == 'POST':
        min_mag = request.form.get('min_mag', 0)
        max_mag = request.form.get('max_mag', 10)

        # Create cache key based on query
        cache_key = hashlib.sha256(f"{min_mag}_{max_mag}".encode()).hexdigest()

        start_time = time.time()

        cached_result = redis_client.get(cache_key)

        if cached_result:
            df = pd.read_json(io.BytesIO(cached_result))
            elapsed_time = time.time() - start_time
            cache_status = "CACHE HIT"
            print(cache_status)
        else:
            cache_status = "CACHE MISS"
            print(cache_status)
            conn = get_connection()
            query = """
                SELECT id, time, latitude, longitude, depth, mag, place
                FROM Earthquakes
                WHERE mag BETWEEN ? AND ?
                ORDER BY time DESC
            """
            df = pd.read_sql(query, conn, params=[min_mag, max_mag])
            conn.close()
            redis_client.setex(cache_key, 300, df.to_json().encode())
  # cache for 5 mins
            elapsed_time = time.time() - start_time

        html_table = df.to_html(classes='table table-striped', index=False).replace('\n', '')

        return render_template(
            'results.html',
            tables=[html_table],
            titles=df.columns.values,
            elapsed_time=f"{elapsed_time:.4f} seconds",
            cache_status=cache_status
        )

    return render_template('query.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            file_path = os.path.join('static', 'uploads', file.filename)
            file.save(file_path)

            df_cleaned = pd.read_csv(file_path, skip_blank_lines=True)

            conn = get_connection()
            cursor = conn.cursor()
            for index, row in df_cleaned.iterrows():
                cursor.execute("""
                    INSERT INTO Earthquakes (id, time, latitude, longitude, depth, mag, place)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, row['id'], row['time'], row['latitude'], row['longitude'], row['depth'], row['mag'], row['place'])
            conn.commit()
            cursor.close()
            conn.close()
            flash('CSV data uploaded successfully (skipped blank lines)!')
            return redirect(url_for('index'))
        else:
            flash('Please upload a valid CSV file.')
            return redirect(url_for('upload'))
    return render_template('upload.html')

if __name__ == '__main__':
    os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
    app.run(debug=True)
