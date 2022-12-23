from bitdotio import bitdotio as bd
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, StringField
from flask_bootstrap import Bootstrap
from mutagen.mp3 import MP3
import os, mutagen, json, model

# PARAMS
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp3'}
bdio_key = "v2_3xCCd_fhprvAiUrwAxJsgV22Dq4Vt"
flask_key= 'MLXH243GssUWwKdTWS7FDhdwYF56wPj8'
db_name = "jdstansil/VGM"

# Instantiate Flask form class
class AddRecord(FlaskForm):
    # id used only by update/edit
    game_name = StringField('Game name')
    ost = SelectField('Is the song part of an original soundtrack?',
                        choices=[('yes', 'yes'),('no', 'no')])
    submit = SubmitField('Add/Update Record')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Populate genres from DB
genres = []
bdb = bd(bdio_key)
with bdb.get_connection(db_name) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT genre FROM songs")
    for record in cursor:
        if str(record[0]) != 'None':
            genres.append(str(record[0]))

# Instantiate model
tree = model.Model()

# Configure app paramaters
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = flask_key
Bootstrap(app)

# Landing page
@app.route('/')
def index():
    return render_template('index.html', genres=genres)

# Song list page
@app.route('/songs/<genre>')
def songs(genre):
    songs = []
    with bdb.get_connection(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM songs WHERE genre = '" + genre + "'")
        for record in cursor:
            songs.append(record)

    return render_template('list.html', songs=songs, genre=genre)

# Upload page. Retrieves metadata for database upload
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)

            audio = MP3(path)
            metadata = dict(mutagen.File(path, easy=True))
            metadata['length'] = [int(audio.info.length)]
            metadata['filename'] = [filename]

            # Format string and remove backslashes to avoid URL errors
            metadata = str(metadata).replace("/", " ").replace("[", "").replace("]", "").replace("'", "\"")

            return redirect(url_for('add_info', metadata=metadata))
    return render_template('upload.html')

@app.route('/add_info/<metadata>', methods=['GET', 'POST'])
def add_info(metadata):
    form = AddRecord()
    if form.validate_on_submit():

        # Read form data
        name = form.game_name.data
        ost = form.ost.data

        # Convert metadata to a dictionary and predict its genre
        metadata = json.loads(metadata)
        res = tree.predict_genre([[metadata.setdefault('date', 0), metadata.setdefault('length', 0)]])
        metadata['genre'] = res[0]

        # Map metadata dictionary to DB upload
        with bdb.get_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO songs (title, album, year, length, game_name, ost, filename, genre)
            VALUES (%s, %s, %s, %s, %s, %s, %s , %s)""",
                           (metadata.setdefault('title', ""),
                            metadata.setdefault('album', ""),
                            metadata.setdefault('date', 0),
                            metadata.setdefault('length', 0),
                            name,
                            ost,
                            metadata.setdefault('filename', ""),
                            metadata.setdefault('genre', "")
                            )
                           )
            conn.commit()

        # Delete the file after we've added its metadata to the DB. This line would be removed if we processed the raw MP3
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], metadata['filename']))
        # Retrain the model on the new data
        # tree.train()

        return redirect(url_for('genre_result', genre=metadata['genre']))
    return render_template('add.html', form=form)

@app.route('/genre_result/<genre>')
def genre_result(genre):
    return render_template('result.html', genre=genre)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)

