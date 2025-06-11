from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import pyodbc
from dotenv import load_dotenv
import os

app = Flask(__name__)
app.secret_key = 'supersecret'  # for flash messages

load_dotenv()
password = os.getenv('SQL_PASSWORD')

server = 'tcp:dbdemo-server.database.windows.net'
database = 'mydb'
username = 'abhi@dbdemo-server'
driver = '{ODBC Driver 18 for SQL Server}'

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
        time = request.form['time']
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
        """, quake_id, time, latitude, longitude, depth, mag, place)
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
        conn = get_connection()
        query = """
            SELECT id, time, latitude, longitude, depth, mag, place
            FROM Earthquakes
            WHERE mag BETWEEN ? AND ?
            ORDER BY time DESC
        """
        df = pd.read_sql(query, conn, params=[min_mag, max_mag])
        conn.close()

        # Remove leading/trailing \n and whitespace in the HTML
        html_table = df.to_html(classes='table table-striped', index=False).replace('\n', '')

        return render_template('results.html', tables=[html_table], titles=df.columns.values)
    return render_template('query.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.csv'):
            file_path = os.path.join('static', 'uploads', file.filename)
            file.save(file_path)

            # Read the cleaned CSV file while skipping blank lines
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
