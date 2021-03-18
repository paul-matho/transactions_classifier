import csv
import re
import hashlib
import json
from selenium import webdriver
import datetime
import os
import logging
import dateutil.parser
import pandas as pd


def configure_logging():
    today_time = datetime.datetime.now().strftime('%d-%m-%Y %I%M%S')
    logfilepath = os.getcwd() + '\\logs\\'
    logfilename = str(today_time) + '.log'
    os.makedirs(logfilepath, mode=0o777, exist_ok=True)

    handlers = [logging.FileHandler(logfilepath+logfilename), logging.StreamHandler()]

    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        level=logging.DEBUG,
                        handlers=handlers)


def import_csv(input_file):
    with open(input_file, "r") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        content = []
        for line in csv_reader:
            content.append(line)
        return content


def setup_webdriver(run_id):
    driver_binary = "C:/Support/chromedriver-2.41.exe"
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-infobars")
    options.add_argument("--start-maximized")
    # options.add_argument('--headless')
    # options.add_argument('--disable-gpu')

    # set download location in Chrome to save file.
    downloads_dir = '{0}\\transactions\\{1}\\'.format(os.getcwd(), run_id)
    os.makedirs(downloads_dir, mode=0o777, exist_ok=True)

    options.add_experimental_option("prefs", {
        "download.default_directory": downloads_dir,
        "profile.default_content_setting_values.notifications": 2,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    driver = webdriver.Chrome(driver_binary, chrome_options=options)
    return driver


class TransactionClassifier:
    categories = 'C:\\Users\\paul_\\OneDrive\\Documents\\version_control\\transaction_classifier\\transactions\\categories.csv'

    def __init__(self):
        # import categories:
        with open(self.categories, "r", encoding='UTF-8') as categories_csv_file:
            categories_csv_reader = csv.DictReader(categories_csv_file, delimiter=',')
            self.categories_list = [line for line in categories_csv_reader]
            for cat in self.categories_list:
                cat['SeedWords'] = cat['SeedWords'].split(',')
                cat['SeedWords'] = [word.strip() for word in cat['SeedWords']]

        categories_csv_file.close()

    def categorise_transaction(self, transaction):
        vendor = transaction['vendor']
        if not vendor:
            return None

        # # try matching words:
        # vendor_words = vendor.upper().replace("'", '').split()
        # vendor_words = [vendor_word.strip() for vendor_word in vendor_words]
        #
        # for category in self.categories_list:
        #     match = set(vendor_words) & set(map(lambda x: x.upper(), category['SeedWords']))
        #     if match:
        #         return category['Category']

        # try matching phrase:
        vendor = vendor.upper().replace("'", '').strip()

        for category in self.categories_list:
            for seed_word in category['SeedWords']:
                if seed_word.upper() in vendor:
                    return category['Category']

        return None


class IngUtils:
    """
    Class for processing ING transactions.
    """
    ing_desc_regex = {'vendor': '(.*?)(?=-)',
                      'type': '(?<=-)(.*?)(?=-)',
                      'receipt': '(?<=Receipt)(.*?)(?=In|To|Date)',
                      'location': '(?<=In)(.*?)(?=Date)',
                      'trans_date': '(?<=Date)(.*?)(?=Card|Time)',
                      'card': '(?<=Card)(.*?)',
                      'to': '(?<=To).+$'}

    def __init__(self):
        self.classifier = TransactionClassifier()

    @staticmethod
    def _get_string(regex, text):
        pattern = re.compile(regex)
        try:
            return pattern.search(text).group()
        except:
            return None

    def calc_transaction_id(self, raw_transaction):
        return hashlib.md5(json.dumps(raw_transaction, sort_keys=True).encode('utf-8')).hexdigest()

    @staticmethod
    def _locate_dash(desc):
        """
        This method is used to remove unhelpful dashes that exist in the raw description, such as '7-ELEVEN'.
        :param desc:
        :return:
        """
        desc_ret = desc
        d_strings = ['7-', 'P-']
        for d_string in d_strings:
            idx = desc.find(d_string)
            if idx > -1:
                desc_list = list(desc)
                desc_list[idx + 1] = ' '
                desc_ret = "".join(desc_list)
        return desc_ret

    def parse_ing_description(self, description: str):
        """
        The description field in the raw ING files comes as a continuous descriptive string separated with dashes.
        This method parses the raw description string using regex.

        :param description: raw descriptive string containing dashes.
        :return: description as dict.
        """
        description = self._locate_dash(description)
        description_dict = {k: self._get_string(v, description) for (k, v) in self.ing_desc_regex.items()}
        return description_dict

    def format_transaction(self, raw_transaction):
        """
        Place the current transaction in a format suitable for uploading to the db.
        :return:
        """
        new_description = self.parse_ing_description(raw_transaction['Description'])

        transaction_output = {}
        transaction_output['id'] = self.calc_transaction_id(raw_transaction)
        transaction_output['date'] = datetime.datetime.strptime(raw_transaction['Date'], '%d/%m/%Y')
        if new_description['trans_date']:
            transaction_output['trans_date'] = dateutil.parser.parse(new_description['trans_date'])
        else:
            transaction_output['trans_date'] = transaction_output['date']
        transaction_output['vendor'] = new_description['vendor']
        transaction_output['location'] = new_description['location']

        # derive 'amount':
        if raw_transaction['Debit'] != '':
            transaction_output['amount'] = round(float(raw_transaction['Debit'].replace(',','')), 2)
        if raw_transaction['Credit'] != '':
            transaction_output['amount'] = round(float(raw_transaction['Credit'].replace(',','')), 2)

        transaction_output['account'] = 'ing'
        transaction_output['category'] = self.classifier.categorise_transaction(transaction_output)

        if transaction_output['category']:
            transaction_output['ml'] = 0
        else:
            transaction_output['ml'] = 1

        return transaction_output

    def validate_transaction(self, processed_transaction):
        """
        Check that the transaction is ok to add to the dataframe.
        :return: True if the transaction is NOT a visa card or PayPal payment
        """

        restricted_transactions = ['PAYPAL', 'visa', 'Transfer', 'Plm payment', 'CC payment']

        if processed_transaction['vendor']:
            for trans in restricted_transactions:
                if trans.upper() in processed_transaction['vendor'].upper():
                    return False
            return True
        else:
            return False


class NabUtils:
    def __init__(self, account='nab_paul'):
        self.classifier = TransactionClassifier()
        self.account = account

    def calc_transaction_id(self, raw_transaction):
        return hashlib.md5(json.dumps(raw_transaction, sort_keys=True).encode('utf-8')).hexdigest()

    def create_header(self, filename):
        cols = ["Date", "Amount", "Card", " ", "Type", "Vendor", "Balance"]
        nab_df = pd.read_csv(filename)
        if (list(nab_df.columns) == cols):
            return
        nab_df.columns = ["Date", "Amount", "Card", " ", "Type", "Vendor", "Balance"]
        nab_df.to_csv(filename, index=False)

    def format_transaction(self, raw_transaction):
        transaction_output = {}
        transaction_output['id'] = self.calc_transaction_id(raw_transaction)
        try:
            transaction_output['date'] = datetime.datetime.strptime(raw_transaction['Date'], '%d-%b-%y')
        except ValueError:
            transaction_output['date'] = datetime.datetime.strptime(raw_transaction['Date'], '%d %b %y')
        transaction_output['trans_date'] = transaction_output['date']
        transaction_output['vendor'] = raw_transaction['Vendor']
        transaction_output['location'] = ''
        transaction_output['amount'] = round(float(raw_transaction['Amount'].replace(',','')), 2)
        transaction_output['account'] = self.account
        transaction_output['category'] = self.classifier.categorise_transaction(transaction_output)
        if transaction_output['category']:
            transaction_output['ml'] = 0
        else:
            transaction_output['ml'] = 1

        return transaction_output

    def validate_transaction(self, processed_transaction):
        if processed_transaction['vendor'] != 'CASH/TRANSFER PAYMENT - THANK YOU':
            return True
        else:
            return False


class PaypalUtils:
    def __init__(self):
        self.classifier = TransactionClassifier()

    def calc_transaction_id(self, raw_transaction):
        return hashlib.md5(json.dumps(raw_transaction, sort_keys=True).encode('utf-8')).hexdigest()

    def filter_rows(self, filename):
        paypal_df = pd.read_csv(filename)
        paypal_df = paypal_df[(paypal_df['Status'] == 'Completed') & ((paypal_df['Type'] == 'eBay Auction Payment') | (paypal_df['Type'] == 'Express Checkout Payment'))]
        paypal_df.to_csv(filename, index=False, encoding='utf-8')

    def format_transaction(self, raw_transaction):
        transaction_output = {}
        transaction_output['id'] = self.calc_transaction_id(raw_transaction)
        try:
            raw_transaction['Date'] = raw_transaction['\ufeff"Date"']
        except KeyError:
            raw_transaction['Date'] = raw_transaction['Date']
        transaction_output['date'] = datetime.datetime.strptime(raw_transaction['Date'], '%d/%m/%Y').strftime('%Y/%m/%d')
        transaction_output['trans_date'] = transaction_output['date']
        transaction_output['vendor'] = raw_transaction['Name']
        transaction_output['location'] = ''
        transaction_output['amount'] = round(float(raw_transaction['Amount'].replace(',','')), 2)
        transaction_output['account'] = 'paypal'
        transaction_output['category'] = self.classifier.categorise_transaction(transaction_output)
        if transaction_output['category']:
            transaction_output['ml'] = 0
        else:
            transaction_output['ml'] = 1

        return transaction_output

    def validate_transaction(self, processed_transaction):
        return True


def rename_transaction_file(downloads_dir, run_id, type='ing', who='paul'):
    filelist = os.listdir(downloads_dir)
    if type == 'ing':
        for file in filelist:
            if file == 'Transactions.csv':
                os.rename('{}Transactions.csv'.format(downloads_dir),
                          '{0}transactions_ing_{1}.csv'.format(downloads_dir, run_id))
    if type == 'nab':
        for file in filelist:
            if file == 'TransactionHistory.csv':
                os.rename('{}TransactionHistory.csv'.format(downloads_dir),
                          '{0}transactions_nab_{1}_{2}.csv'.format(downloads_dir, run_id, who))
    if type == 'paypal':
        for file in filelist:
            if file == 'Download.CSV':
                os.rename('{}Download.CSV'.format(downloads_dir),
                          '{0}transactions_paypal_{1}.csv'.format(downloads_dir, run_id))

