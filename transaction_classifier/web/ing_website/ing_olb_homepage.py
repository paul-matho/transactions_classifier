import logging
from time import sleep
import transaction_classifier.web.base_elements as be


logger = logging.getLogger(__name__)

class IngOnlineBankingHomepage(be.BasePage):
    def __init__(self, driver):
        be.BasePage.__init__(self, driver)
        self.driver = driver

        # Buttons:
        self.buttons.export_dropdown = be.BaseButton(driver, xpath='//*[@id="aggregateTransactions"]/div[1]/div[2]/div[4]/ing-dropdown-actions-button/paper-menu-button/div/paper-button', name='IngOnlineBankingHomepage..buttons.export')
        self.buttons.export_csv = be.BaseButton(driver, xpath='//span[text()="CSV (Excel)"]', name='IngOnlineBankingHomepage.buttons.export_csv')

        self.buttons.logout = be.BaseButton(driver, xpath='//ing-page-block[@id="wrapper"]/div/ing-layout/div/div/div/div[3]/button', name='IngOnlineBankingHomepage.buttons.logout')
