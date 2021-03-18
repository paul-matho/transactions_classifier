import logging
from time import sleep
import transaction_classifier.web.base_elements as be


logger = logging.getLogger(__name__)

class NabOnlineBankingHomepage(be.BasePage):
    def __init__(self, driver):
        be.BasePage.__init__(self, driver)
        self.driver = driver

        self.buttons.logout = be.BaseButton(driver, xpath='//button[@id="logoutButton"]')
        self.buttons.first_account = be.BaseButton(driver, xpath='//span[text()=" 4557025667683649 "]')

    def logout(self):
        self.buttons.logout.click()
        sleep(1)
        alert = self.driver.switch_to.alert
        print(alert.text)
        alert.accept()


class NabTransactionHistoryPage(be.BasePage):
    def __init__(self, driver):
        be.BasePage.__init__(self, driver)
        self.driver = driver

        # buttons:
        self.buttons.show_filter = be.BaseButton(driver, xpath='//*[@id="transactions"]/div/app-component/ib-transactions/div/div/div/ib-filter/div/form/div/div[1]/div/div[2]/div[2]/button')
        self.buttons.display = be.BaseButton(driver, xpath='//button[@id="displayBtn"]')
        self.buttons.export = be.BaseButton(driver, xpath='//button[@id="exportTransactionsBtn"]')

        # button dropdown
        self.buttons.date_range_dropdown = be.BaseButton(driver, xpath='//*[@id="input-transaction-period"]/a')
        self.buttons.this_financial_year = be.BaseButton(driver, xpath='//span[text()="This financial year"]')
        self.buttons.last_financial_year = be.BaseButton(driver, xpath='//span[text()="Last financial year"]')
