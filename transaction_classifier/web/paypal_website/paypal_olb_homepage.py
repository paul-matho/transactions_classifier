import logging
from time import sleep
import web.base_elements as be


logger = logging.getLogger(__name__)


class PaypalHomepage(be.BasePage):
    def __init__(self, driver):
        be.BasePage.__init__(self, driver)
        self.driver = driver

        # tabs:
        self.tabs.activity = be.BaseButton(driver, xpath='//a[@id="header-activity"]')
        self.buttons.logout = be.BaseButton(driver, xpath='//a[@id="header-logout"]')


class PaypalActivity(be.BasePage):
    def __init__(self, driver):
        be.BasePage.__init__(self, driver)
        self.driver = driver

        # buttons
        self.buttons.statements = be.BaseButton(driver, xpath='//div[@id="js_runningBalanceView"]/ul/li/button')
        self.buttons.download_detailed_statements = be.BaseButton(driver, xpath='//section[@id="js_statementView"]/div/section/ul/li/a/div/div[1]')

        # activity download
        self.buttons.data_range_dropdown = be.BaseButton(driver, xpath='//*[@id="react-datepicker-dropdown-epmlhk"]/button')
        self.fields.input_from = be.BaseField(driver, xpath='//input[@id="inpFrom"]')
        self.fields.input_to = be.BaseField(driver, xpath='//input[@id="inpTo"]')
        self.buttons.date_range_ok = be.BaseButton(driver, xpath='//*[@id="react-datepicker-dropdown-epmlhk"]/ul/li[10]/span/button')

