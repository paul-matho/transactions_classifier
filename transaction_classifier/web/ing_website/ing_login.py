import logging
from time import sleep
import urllib.request
import transaction_classifier.web.base_elements as be
import numpy as np
import cv2
import os

logger = logging.getLogger(__name__)


class IngLoginPage(be.BasePage):

    def __init__(self, driver, url = None):
        be.BasePage.__init__(self, driver)
        self.driver = driver
        self.login_urls = {'landing_page': 'https://www.ing.com.au/',
                           'online_banking_login': 'https://www.ing.com.au/securebanking/'}

        if url is None:
            self.url = self.login_urls['landing_page']
        else:
            self.url = url

        # Buttons:
        self.buttons.landing_page_login = be.BaseButton(driver, xpath='//div[@id="login-menu-button"]/a/div/div')
        self.buttons.login = be.BaseButton(driver, xpath='//button[@id="login-btn"]')

        # Fields:
        self.fields.client_number = be.BaseField(driver, xpath='//input[@id="cifField"]')

        # Special class: ING login keypad:
        self.keypad = IngLoginKeypad(driver)


    def login(self, creds):
        logger.info('Logging in to ING')
        self.driver.get(self.url)
        sleep(8)
        if self.url == self.login_urls['landing_page']:
            self.buttons.landing_page_login.click()
            sleep(8)
        self.fields.client_number.click()
        sleep(4)
        self.fields.client_number.send_keys(creds['id'])
        sleep(4)
        self.keypad.refresh_keypad()
        self.keypad.key_sequence(creds['p'])
        sleep(4)
        self.buttons.login.click()


def get_model():
    """ Need to run this as there is no reliable save and reload function for cv2 classifiers """
    samples_path = os.path.realpath('./transaction_classifier/web/ing_website/generalsamples.data').replace('\\', '/')
    resp_path = os.path.realpath('./transaction_classifier/web/ing_website/generalresponses.data').replace('\\', '/')
    samples = np.loadtxt(samples_path, np.float32)
    responses = np.loadtxt(resp_path, np.float32)
    responses = responses.reshape((responses.size, 1))
    model = cv2.ml.KNearest_create()
    model.train(samples, cv2.ml.ROW_SAMPLE, responses)
    return model


def get_number(im, model):
    dims = im.shape
    trim = 20
    im_reduced = im[trim:dims[1] - trim, trim:dims[2] - trim].copy()
    # out = np.zeros(im_reduced.shape, np.uint8)
    gray = cv2.cvtColor(im_reduced, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, 1, 1, 11, 2)
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    output = None

    for cnt in contours:
        if cv2.contourArea(cnt) > 50:
            [x, y, w, h] = cv2.boundingRect(cnt)
            if h > 28:
                cv2.rectangle(im_reduced, (x, y), (x + w, y + h), (0, 255, 0), 2)
                roi = thresh[y:y + h, x:x + w]
                roismall = cv2.resize(roi, (10, 10))
                roismall = roismall.reshape((1, 100))
                roismall = np.float32(roismall)
                retval, results, neigh_resp, dists = model.findNearest(roismall, k=1)
                output = int((results[0][0]))

    return output


def url_to_image(url):
    # download the image, convert it to a NumPy array, and then read it into OpenCV format
    resp = urllib.request.urlopen(url)
    image = np.asarray(bytearray(resp.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    return image


class IngLoginButton(object):
    def __init__(self, model, elem):
        self.elem = elem
        self.image = url_to_image(elem.get_attribute('src'))
        self.number = get_number(self.image, model)


class IngLoginKeypad(object):
    def __init__(self, driver):
        self.driver = driver
        self.model = get_model()
        self.refresh_keypad()

    def refresh_keypad(self):
        image_elems = [elem for elem in self.driver.find_elements_by_tag_name('img')]
        self.buttons = [IngLoginButton(self.model, elem) for elem in image_elems]
        if len(self.buttons) > 0:
            del self.buttons[0], self.buttons[9], self.buttons[10], self.buttons[10]

    def key_sequence(self, sequence):
        for char in sequence:
            num = int(char)
            for btn in self.buttons:
                if btn.number == num:
                    btn.elem.click()
                    sleep(1)

