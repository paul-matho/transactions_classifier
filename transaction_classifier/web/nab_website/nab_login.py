import logging
from time import sleep
import web.base_elements as be


logger = logging.getLogger(__name__)


class NabLoginPage(be.BasePage):

    def __init__(self, driver, url = None):
        be.BasePage.__init__(self, driver)
        self.driver = driver
        self.login_url = 'https://ib.nab.com.au/nabib/index.jsp'

        # Buttons:
        self.buttons.login = be.BaseButton(driver, xpath='//button[@title="Login to NAB Internet banking"]', name='NabLoginPage.buttons.login')

        # Fields:
        self.fields.nab_id = be.BaseField(driver, xpath='//input[@id="userid"]', name='NabLoginPage.fields.nab_id')
        self.fields.password = be.PasswordField(driver, xpath='//input[@id="password"]', name='NabLoginPage.fields.nab_pw')

    def login(self, creds):
        logger.info('Logging in to NAB online banking - NAB ID: ' + creds['id'])
        self.driver.get(self.login_url)

        self.fields.nab_id.send_keys(creds['id'])
        sleep(2)
        self.fields.password.send_keys(creds['p'])
        sleep(2)
        self.buttons.login.click()
