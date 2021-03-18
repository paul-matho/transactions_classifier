import os
import csv
import luigi
import datetime
import keyring as kr
from transaction_classifier.web.ing_website import *
from transaction_classifier.web.nab_website import *
from transaction_classifier.web.paypal_website import *
from transaction_classifier.utils import setup_webdriver, IngUtils, NabUtils, PaypalUtils, configure_logging
import logging
from shutil import copyfile
import pandas as pd
from transaction_classifier.expense_categoriser_ml import train_model
from sqlalchemy import create_engine

from luigi.contrib.mysqldb import CopyToTable, MySqlTarget
from mysql.connector import errorcode, Error

logger = logging.getLogger('luigi-interface')
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)


PATH = os.getcwd()


class FetchIngData(luigi.Task):
    """
    Selenium job for ING data
    """
    run_id = luigi.Parameter()

    def requires(self):
        return None

    def run(self):
        driver = setup_webdriver(self.run_id)

        user = ''
        pw = kr.get_password('olb_1', user)
        creds = {'id': user, 'p': pw}
        ing_login_page = IngLoginPage(driver)
        ing_olb_homepage = IngOnlineBankingHomepage(driver)

        ing_login_page.login(creds)
        sleep(5)
        driver.execute_script("window.scrollTo(0, 300)")
        sleep(5)
        ing_olb_homepage.buttons.export_dropdown.click()
        sleep(5)
        ing_olb_homepage.buttons.export_csv.click()
        sleep(5)
        driver.execute_script("window.scrollTo(0, 0)")
        ing_olb_homepage.buttons.logout.click()
        sleep(1)

    def output(self):
        return luigi.LocalTarget(os.path.join(PATH, 'transactions\\{}\\Transactions.csv'.format(self.run_id)))


class FetchNabData(luigi.Task):
    """
    Selenium job for NAB data
    """
    run_id = luigi.Parameter()

    def requires(self):
        return None

    def run(self):
        driver = setup_webdriver(self.run_id)

        user = ''
        pw = kr.get_password('olb_2', user)
        creds = {'id': user, 'p': pw}

        nab_login_page = NabLoginPage(driver)
        nab_olb_homepage = NabOnlineBankingHomepage(driver)
        nab_transaction_history = NabTransactionHistoryPage(driver)

        nab_login_page.login(creds)
        sleep(5)
        nab_olb_homepage.buttons.first_account.click()
        sleep(2)

        nab_transaction_history.buttons.show_filter.click()
        sleep(2)
        nab_transaction_history.buttons.date_range_dropdown.click()
        sleep(2)
        nab_transaction_history.buttons.this_financial_year.click()
        sleep(2)
        nab_transaction_history.buttons.display.click()
        sleep(2)
        nab_transaction_history.buttons.export.click()
        sleep(2)
        nab_olb_homepage.logout()

    def output(self):
        return luigi.LocalTarget(os.path.join(PATH, 'transactions\\{}\\TransactionHistory.csv'.format(self.run_id)))


class FetchNabDataEttie(luigi.Task):
    """
    Fetching Ettie's NAB transactions from fixed CSV file
    """
    run_id = luigi.Parameter()

    def requires(self):
        return None

    def run(self):
        from_path = os.path.join(PATH, 'transactions\\TransactionHistoryEttie.csv')
        to_path = os.path.join(PATH, 'transactions\\{}\\TransactionHistoryEttie.csv'.format(self.run_id))
        copyfile(from_path, to_path)

    def output(self):
        return luigi.LocalTarget(os.path.join(PATH, 'transactions\\{}\\TransactionHistoryEttie.csv'.format(self.run_id)))


class FetchPaypalData(luigi.Task):
    """
    Selenium job for PayPal data must be run manually (cannot be automated)
    """
    run_id = luigi.Parameter()

    def requires(self):
        return None

    def run(self):
        from_path = os.path.join(PATH, 'transactions\\Download.CSV')
        to_path = os.path.join(PATH, 'transactions\\{}\\Download.CSV'.format(self.run_id))
        copyfile(from_path, to_path)

    def output(self):
        return luigi.LocalTarget(os.path.join(PATH, 'transactions\\{}\\Download.CSV'.format(self.run_id)))


class BaseTransactionProcessor(CopyToTable):
    """
    Base class for all transaction uploads
    """
    host = "localhost"
    database = "banking_db"
    user = "root"
    password = ""
    table = "new_transactions"
    port = "3306"
    columns = ['id', 'date', 'trans_date', 'vendor', 'location', 'amount', 'account', 'category', 'ml']

    def init_copy(self, connection):
        trn_qry = 'TRUNCATE new_transactions;'
        connection.cursor().execute(trn_qry)
        connection.commit()

    def copy(self, connection, file=None):
        """
        Over riding the copy method from the base class to replace odd behaviour of only taking first character of
        column names....
        :param cursor:
        :param file:
        :return:
        """
        values = '({})'.format(','.join(['%s' for i in range(len(self.columns))]))
        columns = '({})'.format(','.join([c for c in self.columns]))
        query = 'INSERT INTO {} {} VALUES {}'.format(self.table, columns, values)
        rows = []

        for idx, row in enumerate(self.rows()):
            rows.append(row)

            if (idx + 1) % self.bulk_size == 0:
                connection.cursor().executemany(query, rows)
                rows = []

        connection.cursor().executemany(query, rows)
        connection.commit()

    def post_copy(self, connection):
        qry = "INSERT INTO transactions " \
              "(SELECT B.* FROM transactions A RIGHT JOIN new_transactions B on A.id = B.id WHERE A.id is NULL);"
        connection.cursor().execute(qry)
        connection.commit()

    def run(self):
        """
        Inserts data generated by rows() into target table.

        If the target table doesn't exist, self.create_table will be called to attempt to create the table.

        Normally you don't want to override this.
        """
        if not (self.table and self.columns):
            raise Exception("table and columns need to be specified")

        connection = self.output().connect()

        # attempt to copy the data into mysql
        # if it fails because the target table doesn't exist
        # try to create it by running self.create_table
        for attempt in range(2):
            try:
                cursor = connection.cursor()
                print("calling init copy...")
                self.init_copy(connection)
                self.copy(connection)
                self.post_copy(connection)
                if self.enable_metadata_columns:
                    self.post_copy_metacolumns(cursor)
            except Error as err:
                if err.errno == errorcode.ER_NO_SUCH_TABLE and attempt == 0:
                    # if first attempt fails with "relation not found", try creating table
                    # logger.info("Creating table %s", self.table)
                    connection.reconnect()
                    self.create_table(connection)
                else:
                    raise
            else:
                break

        # mark as complete in same transaction
        self.output().touch(connection)
        connection.commit()
        connection.close()


class ProcessIngData(BaseTransactionProcessor):
    """
    Upload ING data to database
    """

    def requires(self):
        return [FetchIngData(run_id)]

    def rows(self):
        ing = IngUtils()
        input_obj = self.input()
        csv_file = input_obj[0].open('r')
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for raw_transaction in csv_reader:
            transaction = ing.format_transaction(raw_transaction)
            if ing.validate_transaction(transaction):
                yield tuple([v for k, v in transaction.items()])

    def output(self):
        """
        Returns a MySqlTarget representing the inserted dataset.

        needed to override this to generate a unique update_id based on the run_id
        """
        input_obj = self.input()
        update_id = "{}_ing".format(os.path.basename(os.path.dirname(input_obj[0].fn)))
        return MySqlTarget(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            table=self.table,
            update_id=update_id
        )


class ProcessNabData(BaseTransactionProcessor):
    """
    Upload NAB transactions
    """
    def requires(self):
        return [FetchNabData(run_id)]

    def rows(self):
        nab = NabUtils()
        input_obj = self.input()
        nab.create_header(input_obj[0].fn)
        csv_file = input_obj[0].open('r')
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for raw_transaction in csv_reader:
            transaction = nab.format_transaction(raw_transaction)
            if nab.validate_transaction(transaction):
                yield tuple([v for k, v in transaction.items()])

    def output(self):
        """
        Returns a MySqlTarget representing the inserted dataset.

        needed to override this to generate a unique update_id based on the run_id
        """
        input_obj = self.input()
        update_id = "{}_nab".format(os.path.basename(os.path.dirname(input_obj[0].fn)))
        return MySqlTarget(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            table=self.table,
            update_id=update_id
        )


class ProcessNabDataEttie(BaseTransactionProcessor):
    """
    Upload NAB transactions
    """
    def requires(self):
        return [FetchNabDataEttie(run_id)]

    def rows(self):
        nab = NabUtils(account='nab_ettie')
        input_obj = self.input()
        nab.create_header(input_obj[0].fn)
        csv_file = input_obj[0].open('r')
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for raw_transaction in csv_reader:
            transaction = nab.format_transaction(raw_transaction)
            if nab.validate_transaction(transaction):
                yield tuple([v for k, v in transaction.items()])

    def output(self):
        """
        Returns a MySqlTarget representing the inserted dataset.

        needed to override this to generate a unique update_id based on the run_id
        """
        input_obj = self.input()
        update_id = "{}_nab_ettie".format(os.path.basename(os.path.dirname(input_obj[0].fn)))
        return MySqlTarget(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            table=self.table,
            update_id=update_id
        )


class ProcessPaypalData(BaseTransactionProcessor):
    """
    Upload PayPal transactions
    """
    def requires(self):
        return [FetchPaypalData(run_id)]

    def rows(self):
        paypal = PaypalUtils()
        input_obj = self.input()
        paypal.filter_rows(input_obj[0].fn)
        with open(input_obj[0].fn, 'r', encoding="utf8") as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for raw_transaction in csv_reader:
                transaction = paypal.format_transaction(raw_transaction)
                if paypal.validate_transaction(transaction):
                    yield tuple([v for k, v in transaction.items()])

    def output(self):
        """
        Returns a MySqlTarget representing the inserted dataset.

        needed to override this to generate a unique update_id based on the run_id
        """
        input_obj = self.input()
        update_id = "{}_paypal".format(os.path.basename(os.path.dirname(input_obj[0].fn)))
        return MySqlTarget(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            table=self.table,
            update_id=update_id
        )


class ClassifyUnknownTransactions(luigi.Task):
    """
    Pull all transaction from DB
    Train classifier based on known transactions
    Classify unknown transactions
    Upload to db.
    """
    def requires(self):
        return [ProcessPaypalData()]

    def run(self):
        db = self.input()[0]
        conn = db.connect()
        cursor = conn.cursor()

        trn_qry = 'TRUNCATE new_transactions;'
        cursor.execute(trn_qry)

        qry = "SELECT * FROM banking_db.transactions;"

        transactions_df = pd.read_sql(qry, conn, parse_dates=True)
        transactions_df = transactions_df.fillna(value=np.nan)
        transactions_cat_df = train_model(transactions_df)

        # encoding for Chinese characters:
        transactions_cat_df['vendor'] = transactions_cat_df[['vendor']].apply(lambda x: x[0].encode('utf-8'), axis=1)

        pw = ''
        engine = create_engine(f"mysql://root:{pw}@localhost/banking_db")
        transactions_cat_df.to_sql('new_transactions', con=engine, if_exists='append', index=False)

        join_qry = "UPDATE transactions a INNER JOIN new_transactions b ON a.id = b.id SET a.category = b.category;"
        connection = engine.connect()
        connection.execute(join_qry)


if __name__ == '__main__':
    configure_logging()
    date_format = '%Y%m%d_%H%M%S'
    today_date = datetime.datetime.now().strftime(date_format)
    run_id = 'run_{}'.format(today_date)
    # run_id = 'run_20200726_172411'
    # run_id = 'run_20200802_172157'
    # run_id = 'run_20210214_160109'

    luigi.build([FetchIngData(run_id), FetchNabData(run_id), FetchNabDataEttie(run_id), FetchPaypalData(run_id),
                 ProcessIngData(), ProcessNabData(), ProcessNabDataEttie(), ProcessPaypalData(), ClassifyUnknownTransactions()], workers=1, local_scheduler=True)
