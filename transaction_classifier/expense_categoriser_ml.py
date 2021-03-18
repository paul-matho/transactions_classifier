from sklearn.feature_extraction.text import CountVectorizer
import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import mysql.connector
from sqlalchemy import create_engine


def train_model(transactions_df):
    transactions_df['amount'] = transactions_df['amount'].apply(pd.to_numeric, errors='coerce')
    transactions_df = transactions_df.sort_values(by='trans_date')

    transactions_df = transactions_df.reset_index(drop=True)

    # Create category datatype for ML model:
    transactions_df['category'] = transactions_df['category'].str.upper()

    idx_uncategorised = transactions_df['category'].isnull()
    idx_categorised = transactions_df['category'].notnull()

    print('Number of uncategorised transactions: {}'.format(str(idx_uncategorised.sum())))

    # create categories vector:
    transactions_cat_df = transactions_df.dropna(axis=0, subset=['category'])
    categories = pd.Categorical(transactions_cat_df['category'])
    d = dict(enumerate(categories.categories))

    print(d)

    transactions_uncat_df = transactions_df[idx_uncategorised]
    transactions_uncat_df = transactions_uncat_df.drop('category', axis=1)

    # Create day of week variable
    dates = transactions_df['trans_date'].to_list()
    # dates = [datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S').date() for date in dates]
    day_of_week = [date.weekday() for date in dates]
    day_of_week = np.array(day_of_week).transpose()
    day_of_week = day_of_week[:, None]

    vendors = transactions_df['vendor'].to_list()

    trans_account = transactions_df['account'].to_list()
    trans_account = [x if x is not np.nan else 'nan' for x in trans_account]

    location = transactions_df['location'].to_list()
    location = [x if x is not np.nan else 'nan' for x in location]

    amount = transactions_df['amount'].as_matrix().transpose()
    amount = amount[:, None]

    # Vectorise text variables
    print('Vectorising text variables....')
    vectorizer_vendors = CountVectorizer()
    vector_vendors = vectorizer_vendors.fit_transform(vendors).toarray()

    vectorizer_account = CountVectorizer()
    vector_account = vectorizer_account.fit_transform(trans_account).toarray()

    vectorizer_location = CountVectorizer()
    vector_location = vectorizer_location.fit_transform(location).toarray()

    vector = np.concatenate([amount, day_of_week, vector_vendors, vector_account, vector_location], axis=1)

    vector_uncat = vector[idx_uncategorised]
    vector_cat = vector[idx_categorised]

    X_train, X_test, y_train, y_test = train_test_split(vector_cat, categories.codes, test_size=0.2, random_state=0)

    print('Training model....')
    classifier = RandomForestClassifier(n_estimators=1000, random_state=0)
    classifier.fit(X_train, y_train)

    y_pred = classifier.predict(X_test)

    c_matrix = confusion_matrix(y_test, y_pred)

    # print(confusion_matrix(y_test,y_pred))
    # print(classification_report(y_test,y_pred))
    print(accuracy_score(y_test, y_pred))

    vector_uncat = np.nan_to_num(vector_uncat)
    y_pred_uncat = classifier.predict(vector_uncat)

    y_pred_uncat_text = [d[val] for val in y_pred_uncat]
    transactions_uncat_df['category'] = y_pred_uncat_text
    return transactions_uncat_df


def main():
    # transactions_classified_file = 'C:\\Users\\paul_\\OneDrive\\Documents\\version_control\\transaction_classifier\\transactions\\run_20200802_172157\\Transactions_total.csv'
    # transactions_df = pd.read_csv(transactions_classified_file, parse_dates=['date', 'trans_date'])

    pw = ''
    connection = mysql.connector.connect(user='root',
                                         password=pw,
                                         host='localhost',
                                         port='3306',
                                         database='banking_db',
                                         autocommit=False)
    cursor = connection.cursor()

    trn_qry = 'TRUNCATE new_transactions;'
    cursor.execute(trn_qry)

    qry = "SELECT * FROM banking_db.transactions;"

    transactions_df = pd.read_sql(qry, connection, parse_dates=True)

    transactions_df = transactions_df.fillna(value=np.nan)

    trans_uncat_df = train_model(transactions_df)

    pw = ''
    engine = create_engine(f"mysql://root:{pw}@localhost/banking_db")

    trans_uncat_df['vendor'] = trans_uncat_df[['vendor']].apply(lambda x: x[0].encode('utf-8'), axis=1)

    trans_uncat_df.to_sql('new_transactions', con=engine, if_exists='replace', index=False)

    print('hello')


if __name__ == '__main__':
    main()


# transactions_uncat_df.to_csv('predicted.csv', index=False)
#
# # save the model to disk
# filename_classifier = 'trained_classifier.sav'
# filename_vendor_vectoriser = 'vendor_vectoriser.sav'
# filename_account_vectoriser = 'account_vectoriser.sav'
# filename_location_vectoriser = 'location_vectoriser.sav'
#
# pickle.dump(classifier, open(filename_classifier, 'wb'))
# pickle.dump(vectorizer_vendors, open(filename_vendor_vectoriser, 'wb'))
# pickle.dump(vectorizer_account, open(filename_account_vectoriser, 'wb'))
# pickle.dump(vectorizer_location, open(filename_location_vectoriser, 'wb'))
#
# # some time later...
#
# # load the model from disk
# classifier = pickle.load(open(filename_classifier, 'rb'))
# vectorizer_vendors = pickle.load(open(filename_vendor_vectoriser, 'rb'))
#
# result = classifier.score(X_test, y_test)
# print(result)
