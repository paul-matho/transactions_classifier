from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import *
import logging
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
from retrying import retry
import time
import inspect
import os
import datetime


logger = logging.getLogger(__name__)


class BaseElement(object):
    def __init__(self, driver, xpath, name=None):
        self.driver = driver
        self.xpath = xpath
        if name:
            self.name = name
        return

    @retry(stop_max_attempt_number=1, wait_random_min=5, wait_random_max=10)
    def click(self, driver_wait_time=30, method='standard'):
        if method == 'standard':
            try:
                wait = WebDriverWait(self.driver, driver_wait_time)
                wait.until(ec.visibility_of_element_located((By.XPATH, self.xpath)))
                wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
                self.driver.find_element_by_xpath(self.xpath).click()
                logger.debug('Element clicked: ' + self.name)
            except:
                logging.exception('Failed to click element: ' + self.name)
                raise
        else:
            element = self.driver.find_element_by_xpath(self.xpath)
            action = webdriver.ActionChains(self.driver).click(element).perform()
            logger.debug('Element clicked via non-standard: ' + self.name)
        return

    def click_drag(self, start, finish):
        """
        start = [x,y] of screen position to start dragging
        finish = [x,y] of screen position to finish dragging
        """
        logger.debug('Sorry, click_drag has been disabled.')
        # pyautogui.moveTo(*start)
        # pyautogui.click()

        return

    def move_to_element(self):
        actions = ActionChains(self.driver)
        actions.move_to_element(self.elem).perform()
        return

    def scroll_into_view(self):
        self.driver.execute_script('arguments[0].scrollIntoView();', self.elem)
        return

    @property
    def size(self):
        return self.elem.size

    @property
    def elem(self):
        #
        return self.driver.find_element_by_xpath(self.xpath)

    # @property
    # def geo(self):
    #     elem = self.elem
    #     return ElementGeo(elem)
    #
    @property
    def location(self):
        return self.elem.location

    def is_displayed(self):
        return self.elem.is_displayed()

    def save_screenshot(self):
        filename = f'{self.__class__.__name__}.png'
        self.elem.screenshot(filename)
        return


class MultiElement(BaseElement):
    def __init__(self, driver, xpath, name=None):
        BaseElement.__init__(self, driver, xpath, name)
        return

    def get_elems(self):
        self.elems = self.driver.find_elements_by_xpath(self.xpath)
        return

    @property
    def elem(self):
        self.get_elems()
        for elm in self.elems:
            try:
                logger.debug(f'Trying to click element {self.name}')
                elm.click()
                logger.debug(f'found interactable element for {self.name}')
                return elm
            except Exception as err:
                logger.debug(f'elm not interactable {self.name}')
        return


class BaseField(BaseElement):
    def __init__(self, driver, xpath, name=None):
        BaseElement.__init__(self, driver, xpath)
        if name is None:
            x = inspect.stack()[1].code_context[0]
            self.name = x.strip()[5:x.find("=") - 8].strip()
        else:
            self.name = name
        return

    def send_keys(self, text, driver_wait_time=20):
        wait = WebDriverWait(self.driver, driver_wait_time)
        wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        try:
            self.driver.find_element_by_xpath(self.xpath).send_keys(text)
            if text in Keys.__dict__.values():
                # TODO: need to convert encoded special keys for logging.
                logger.debug('Sent unique selenium KEY to ' + self.name)
            else:
                logger.debug('Sent "' + text + '" to ' + self.name)
        except:
            logger.exception('Exception on BaseField send_keys: ')
            raise
        return

    def clear(self):
        try:
            self.driver.find_element_by_xpath(self.xpath).clear()
            logger.debug('Cleared field: ' + self.name)
        except:
            logger.exception('Exception on BaseField clear: ')
            pass
        return

    def get_attribute(self, attr):
        try:
            wait = WebDriverWait(self.driver, 20)
            wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
            value = self.driver.find_element_by_xpath(self.xpath).get_attribute(attr)
            logger.debug('Got attribute: ' + attr + ' from ' + self.name + '. Value: ' + value)
            return value
        except:
            logger.exception('Exception on BaseField get_attribute.')
            raise

    def enter_keys(self, text):
        self.send_keys(text)
        self.send_keys(Keys.ENTER)
        return

    def send_keys_js(self, text, state=None):
        """
        Same as send_keys() however send the keys using javascript
        """
        self.driver.execute_script("arguments[0].value = arguments[1];", self.elem, text)
        # elem.send_keys(Keys.SPACE)      # JavaScript method above doesn't register text entry for remedy
        # elem.send_keys(Keys.BACKSPACE)
        # elem.send_keys(Keys.TAB)
        return

    def is_text_entered(self, text, driver_wait_time=20, max_tries=5):
        wait = WebDriverWait(self.driver, driver_wait_time)
        wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        curr_try = 1
        while (curr_try < max_tries) and not (
                self.driver.find_element_by_xpath(self.xpath).get_attribute(self.__text_attribute) == text):
            time.sleep(2)
            curr_try += 1
        else:
            if (self.driver.find_element_by_xpath(self.xpath).get_attribute(self.__text_attribute) == text):
                logger.debug('text entered validated')
                return True
            else:
                logger.debug('text entered invalid')
                return False

    def wait_click(self, driver_wait_time=20, method='standard'):
        print('Trying to click Route Work Flow')
        for i in range(0, 100):
            time.sleep(1)
            try:
                print('Attempt {} at clicking Route Workflow'.format(i))
                self.click()
                break
            except Exception:
                pass
        return

    def wait_until_populated(self, driver_wait_time=20, max_tries=5):
        wait = WebDriverWait(self.driver, driver_wait_time)
        wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        curr_try = 1
        while (curr_try < max_tries) and not (
        self.__re_match, self.driver.find_element_by_xpath(self.xpath).get_attribute(self.__text_attribute)):
            time.sleep(2)
            curr_try += 1
        else:
            if re.match(self.__re_match,
                        self.driver.find_element_by_xpath(self.xpath).get_attribute(self.__text_attribute)):
                # self.logger.log('wait till text to be entered: complete')
                return True
            else:
                # self.logger.log('wait till text to be entered: fail')
                return False
            return

    def is_populated(self):
        if re.match(self.__re_match,
                    self.driver.find_element_by_xpath(self.xpath).get_attribute(self.__text_attribute)):
            # self.logger.log('text is present')
            return True
        else:
            # self.logger.log('text is not present')
            return False
        return False

    @property
    def text(self):
        elem = self.driver.find_element_by_xpath(self.xpath)
        return elem.text

    @property
    def bs4_soup(self):
        return BeautifulSoup(self.driver.page_source, 'html.parser')


class PasswordField(BaseField):
    def __init__(self, driver, xpath, name=None):
        BaseField.__init__(self, driver, xpath, name)
        if name is None:
            x = inspect.stack()[1].code_context[0]
            self.name = x.strip()[5:x.find("=") - 8].strip()
        else:
            self.name = name
        return

    def send_keys(self, text, driver_wait_time=20):
        """
        Override so that pwd is not logged
        """
        wait = WebDriverWait(self.driver, driver_wait_time)
        wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        try:
            self.driver.find_element_by_xpath(self.xpath).send_keys(text)
            if text in Keys.__dict__.values():
                # TODO: need to convert encoded special keys for logging.
                logger.debug('Sent unique selenium KEY to ' + self.name)
            else:
                logger.debug('Sent password to {}'.format(self.name))
        except:
            logger.exception('Exception on BaseField send_keys: ')
            raise
        return


class MultiField(MultiElement):
    def __init__(self, driver, xpath, name=None):
        MultiElement.__init__(self, driver, xpath, name)
        return

    def send_keys(self, text, driver_wait_time=20):
        wait = WebDriverWait(self.driver, driver_wait_time)
        # wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        try:
            self.elem.send_keys(text)
            if text in Keys.__dict__.values():
                # TODO: need to convert encoded special keys for logging.
                logger.debug('Sent unique selenium KEY to ' + self.name)
            else:
                logger.debug('Sent "' + text + '" to ' + self.name)
        except Exception as err:
            logger.exception('{err}')
            logger.exception('Exception on BaseField send_keys: {self.name}')
            raise
        return


class SimpleField(BaseField):
    def __init__(self, driver, xpath, name=None):
        BaseField.__init__(self, driver, xpath, name)
        self.xpath = xpath
        self.driver = driver


class BaseButton(BaseElement):
    def __init__(self, driver, xpath, name=None):
        BaseElement.__init__(self, driver, xpath)
        if name is None:
            x = inspect.stack()[1].code_context[0]
            self.name = x.strip()[5:x.find("=") - 8].strip()
        else:
            self.name = name
        return

    def hover_mouse_over(self, driver_wait_time=20):
        try:
            wait = WebDriverWait(self.driver, driver_wait_time)
            wait.until(ec.visibility_of_element_located((By.XPATH, self.xpath)))
            element = self.driver.find_element_by_xpath(self.xpath)
            webdriver.ActionChains(self.driver).move_to_element(element).perform()
            logger.debug('Hovered mouse over button: ' + self.name)
        except:
            logging.exception('Failed to hover over button: ' + self.name)
            raise
        return

    def wait_until_clickable(self, driver_wait_time=20, max_tries=5):
        wait = WebDriverWait(self.driver, driver_wait_time)
        wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        curr_try = 1
        while (curr_try < max_tries) and not (
        self.__re_match, self.driver.find_element_by_xpath(self.xpath).get_attribute(self.__text_attribute)):
            time.sleep(1)
            curr_try += 1
        else:
            if re.match(self.__re_match,
                        self.driver.find_element_by_xpath(self.xpath).get_attribute(self.__text_attribute)):
                # self.logger.log('wait till text to be entered: complete')
                return True
            else:
                # self.logger.log('wait till text to be entered: fail')
                return False
            return

    def wait_click(self, driver_wait_time=20, method='standard'):
        # asdf
        print('Trying to click {}'.format(__name__))
        for i in range(0, 100):
            time.sleep(1)
            try:
                print('Attempt {} at clicking {}'.format(i, __name__))
                self.click()
                break
            except Exception:
                pass
        return


class MultiButton(MultiElement, BaseButton):
    def __init__(self, driver, xpath, name):
        BaseButton.__init__(self, driver, xpath, name)
        return

    def click(self, driver_wait_time=30, method='standard'):
        if method == 'standard':
            try:
                wait = WebDriverWait(self.driver, driver_wait_time)
                wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
                self.elem.click()
                logger.debug('Element clicked: ' + self.name)
            except WebDriverException:
                self.driver.execute_script("arguments[0].click();", self.elem)
                logger.debug('Element clicked via javascript: ' + self.name)
            except:
                logging.exception('Failed to click element: ' + self.name)
                raise
        else:
            element = self.driver.find_element_by_xpath(self.xpath)
            action = webdriver.ActionChains(self.driver).click(element).perform()
            logger.debug('Element clicked via non-standard: ' + self.name)
        return


class SimpleButton(BaseButton):
    def __init__(self, driver, xpath):
        BaseButton.__init__(self, driver, xpath)
        self.xpath = xpath
        self.driver = driver


class MaybeButton(BaseButton):
    def __init__(self, driver, xpath, html):
        BaseButton.__init__(self, driver, xpath)
        self.html_to_find = html

    def is_present(self):
        if self.html_to_find in self.driver.page_source:
            return True
        else:
            return False


class JavaScriptButton(BaseButton):
    def __init__(self, driver, javascript, xpath=None):
        if xpath is None:
            xpath = ''
        BaseButton.__init__(self, driver, xpath)
        self.javascript = javascript

    def click(self):
        self.driver.execute_script(self.javascript)


class BaseDropDown(object):
    def __init__(self, driver, xpath, name=None):
        # TODO: need to add exception handling in this class.
        self.driver = driver
        self.xpath = xpath
        if name is None:
            x = inspect.stack()[1].code_context[0]
            self.name = x.strip()[5:x.find("=") - 8].strip()
        else:
            self.name = name
        return

    def click(self, driver_wait_time=20):
        wait = WebDriverWait(self.driver, driver_wait_time)
        wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        self.driver.find_element_by_xpath(self.xpath).click()
        logger.debug('dropdown {} clicked'.format(self.name))
        return

    @property
    def _options(self):
        self.element = self.driver.find_element_by_xpath(self.xpath)
        options = self.element.find_elements_by_tag_name("option")
        return [x.text for x in options]

    def choose_option(self, value):
        logger.debug('Selecting "' + value + '" from ' + self.name + ' dropdown')
        s2 = Select(self.driver.find_element_by_xpath(self.xpath))
        if len(s2.all_selected_options) > 0:
            if value is s2.all_selected_options[0].text:
                return
        s2.select_by_index(self._options.index(value))
        return

    def send_keys(self, text, driver_wait_time=20):
        wait = WebDriverWait(self.driver, driver_wait_time)
        wait.until(ec.element_to_be_clickable((By.XPATH, self.xpath)))
        try:
            self.driver.find_element_by_xpath(self.xpath).send_keys(text)
            # logger.debug(f'Key pressed {text}')
            if text in Keys.__dict__.values():
                # TODO: need to convert encoded special keys for logging.
                logger.debug('Sent unique selenium KEY to ' + self.name)
            else:
                logger.debug('Sent unique key to ' + self.name)
        except:
            logger.exception('Exception on BaseField send_keys: ')
            raise
        return

    def send_keys_1(self, direction='Down'):
        logger.debug(f'Sending keys {direction} to {self.name}')
        self.element = self.driver.find_element_by_xpath(self.xpath)
        try:
            if direction.lower() == 'down':
                self.element.send_keys(Keys.DOWN)
                logger.debug(f'Moved 1 key down {self.name}')
            else:
                self.element.send_keys(Keys.UP)
                logger.debug(f'Moved 1 key up {self.name}')

        except Exception as err:
            logger.debug('Sending keys via action chains')
            action = ActionChains(self.driver)
            if direction.lower() == 'down':
                action.send_keys(Keys.DOWN)
                logger.debug(f'Moved 1 key down {self.name}')
                return
            else:
                action.send_keys(Keys.UP)
                logger.debug(f'Moved 1 key up {self.name}')
            action.perform()
            return
        return


def get_xpath(tag):
    """ This method creates a dynamic xpath given a tag object from BeautifulSoup."""
    xpath = ''
    text = tag.text.strip()
    attrs = {k: v for k, v in tag.attrs.items() if isinstance(v, str)}
    # attrs = [(k,v) for k, v in tag.attrs.items() if isinstance(v, str)]
    attrs_list = list(attrs.items())
    if len(attrs_list) > 1:
        xpath = '//' + tag.name + '[@' + attrs_list[0][0] + '="' + attrs_list[0][1] + '" and @' + attrs_list[1][
            0] + '="' + attrs_list[1][1] + '"]'
    elif len(attrs_list) == 1:
        xpath = '//' + tag.name + '[@' + attrs_list[0][0] + '="' + attrs_list[0][1] + '"]'
    elif len(text) > 0:
        xpath = '//' + tag.name + '[contains(text(),"' + text + '")]'
    return xpath


class TableButton(BaseButton):
    def __init__(self, driver, tag, base_xpath):
        self.driver = driver
        self.tag = tag
        self._cell_xpath = base_xpath
        self.xpath = self._cell_xpath + get_xpath(tag)
        super().__init__(driver, xpath=self.xpath)


class TableField(BaseField):
    def __init__(self, driver, tag, base_xpath):
        self.driver = driver
        self.tag = tag
        self._cell_xpath = base_xpath
        self.xpath = self._cell_xpath + get_xpath(tag)
        super().__init__(driver, xpath=self.xpath)

    @property
    def text(self):
        try:
            return self.tag.attrs['value'].strip()
        except:
            return self.tag.text.strip()


class TableDropDown(BaseDropDown):
    def __init__(self, driver, tag, base_xpath):
        self.driver = driver
        self.tag = tag
        self._cell_xpath = base_xpath
        self.xpath = self._cell_xpath + get_xpath(tag)
        super().__init__(driver, xpath=self.xpath)


class TableCell(BaseButton):
    def __init__(self, driver, tag, base_xpath):
        self.driver = driver
        self.tag = tag
        self.text = tag.text
        self._row_xpath = base_xpath
        self.xpath = self._row_xpath + get_xpath(tag)

        # check for interactive cell contents - firstly for text field outputs
        self.fields = [TableField(self.driver, field, self.xpath) for field in
                       self.tag.findAll(lambda tag: tag.name == 'input')]
        if len(self.fields) > 0:
            self.text = self.fields[0].text.strip()

        # then for drop-downs:
        self.dropdowns = [TableDropDown(self.driver, dropdown, self.xpath) for dropdown in
                          self.tag.findAll(lambda tag: tag.name == 'select')]

        # For now, everything else is a button:
        self.buttons = [TableButton(self.driver, button, self.xpath) for button in
                        self.tag.findAll(lambda tag: tag.name != 'input')]

        BaseButton.__init__(self, driver, xpath=self.xpath)


class TableHeader(BaseButton):
    def __init__(self, driver, tag, base_xpath):
        self.driver = driver
        self.tag = tag
        self.text = tag.text.strip()
        self._table_xpath = base_xpath
        self.xpath = self._table_xpath + get_xpath(tag)
        super().__init__(driver, xpath=self.xpath)


class TableRow(BaseButton):
    def __init__(self, driver, tag, header_keys, base_xpath):
        self.driver = driver
        self.tag = tag
        self.text = tag.text
        self._table_xpath = base_xpath
        self.xpath = self._table_xpath + get_xpath(tag)
        cells = [TableCell(self.driver, cell, self.xpath) for cell in self.tag.findAll(lambda tag: tag.name == 'td')]
        if len(cells) == len(header_keys):
            self.cells = dict(zip(header_keys, cells))
        elif len(header_keys) < len(cells):
            header_keys.append(str(len(header_keys)))
            self.cells = dict(zip(header_keys, cells))
        else:
            self.cells = dict(zip(range(len(cells)), cells))
        super().__init__(driver, xpath=self.xpath)


class BaseTable(object):
    """
    To click on the first field, on the top row (of the table), in the column called "Work Order"
    tablename.rows[1].cells['Work Order'].fields[0].click() #row[0]
    rows[0] is hidden, so top most row is row[1]
    """

    def __init__(self, driver, identifier):
        self.driver = driver
        self.identifier = identifier
        self.only_table_tags = SoupStrainer("table")
        self.xpath = '//table[@' + identifier['attribute'] + '="' + identifier['value'] + '"]'
        # self.refresh_table()

    def refresh_table(self):
        try:
            self.bs = BeautifulSoup(self.driver.page_source, features="lxml", parse_only=self.only_table_tags)
            self.table = self.bs.find(
                lambda tag: tag.name == 'table' and tag.has_attr(self.identifier['attribute']) and self.identifier[
                    'value'] in tag[self.identifier['attribute']])
            headers = [TableHeader(self.driver, header, self.xpath) for header in
                       self.table.findAll(lambda tag: tag.name == 'th')]
            header_keys = [key.text.strip() if (len(key.text.strip()) > 0) else str(idx) for (idx, key) in
                           enumerate(headers)]
            self.headers = dict(zip(header_keys, headers))
            self.rows = [TableRow(self.driver, row, header_keys, self.xpath) for row in
                         self.table.findAll(lambda tag: tag.name == 'tr')]
            del headers, header_keys
            return True
        except AttributeError:
            logger.debug('Table ' + self.identifier['value'] + ' does not exist yet.')
            time.sleep(2)
            return False

    def get_idx_of_row_containing_text(self, row_specific_text):
        # returns the index of a row which contains some specific text
        self.refresh_table()
        # First, try a simple iteration over the row.text property
        row_idx = [idx for (idx, row) in enumerate(self.rows) if row_specific_text in row.text]
        # failing that, iterate over the text contents of each cell in each row:
        if not row_idx:
            row_idx = [idx for (idx, row) in enumerate(self.rows) for key, value in row.cells.items() if
                       row_specific_text in value.text]
        return row_idx
