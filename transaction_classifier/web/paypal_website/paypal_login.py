import logging
from time import sleep
import web.base_elements as be


logger = logging.getLogger(__name__)


class PaypalLoginPage(be.BasePage):
    def __init__(self, driver):
        be.BasePage.__init__(self, driver)
        self.driver = driver
        self.login_url = 'https://www.paypal.com/signin'

        # fields
        self.fields.email = be.BaseField(driver, xpath='//input[@id="email"]')
        self.fields.password = be.PasswordField(driver, xpath='//input[@id="password"]')

        # buttons
        self.buttons.next = be.BaseButton(driver, xpath='//button[@id="btnNext"]')
        self.buttons.login = be.BaseButton(driver, xpath='//button[@id="btnLogin"]')

    def login(self, creds):
        logger.info('Logging in to Paypal')
        self.driver.get(self.login_url)

        self.fields.email.send_keys(creds['id'])
        self.buttons.next.click()
        sleep(1)
        self.fields.password.send_keys(creds['p'])
        self.buttons.login.click()
