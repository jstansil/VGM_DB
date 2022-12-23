import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import create_engine


# Model for genre prediction
class Model:
    # Read data from the VGM database
    def read_db(self):
        alchemyEngine = create_engine('postgresql://jdstansil:v2_3xDaV_MenrbQVbgdS6Kt77m8VXwVP@db.bit.io/jdstansil/VGM',
                                      pool_recycle=3600);
        dbConnection = alchemyEngine.connect();
        song_data = pd.read_sql("SELECT * FROM songs", dbConnection);
        dbConnection.close();
        return song_data;

    # Train the decision tree model on VGM data
    def train(self):
        data = self.read_db()

        # Filter nulls
        cols = ['genre', 'year', 'length']
        data = data[data[cols].notna().all(1)]

        X = data[['year', 'length']]
        y = data['genre']
        X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=10)

        self.tree.fit(X_train, y_train)

    # Return a genre prediction from a np.array
    def predict_genre(self, row):
        return self.tree.predict(row)

    def __init__(self):
        self.tree = DecisionTreeClassifier()
        self.train()