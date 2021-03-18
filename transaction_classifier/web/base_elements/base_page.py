from types import SimpleNamespace
from selenium.webdriver.common.keys import Keys


class BasePage(object):
    def __init__(self, driver):
        self.session = driver
        self.driver = driver
        self.fields = SimpleNamespace()
        self.buttons = SimpleNamespace()
        self.dropdowns = SimpleNamespace()
        self.tabs = SimpleNamespace()
        self.popups = SimpleNamespace()
        self.tables = SimpleNamespace()
        return

    @property
    def html(self):
        return self.driver.page_source

    def save_screenshot(self,filename):
        self.driver.save_screenshot(filename)
        return
    
    def screenshot_self(self):
        self.save_screenshot(f'{self.__class__.__name__}.png')
        return
    
    def screenshot_error(self):
        filename = self.save_screenshot(f"{error: arrow.now().format('hh:mm:')}.png")
        return
    
    def save(self,filename,text = None):
        if text is None:
            text = self.html
        with open(filename,'w') as f:
            f.write(text)
        return

    def close_tab(self):
        elem = self.driver.find_element_by_tag_name("body")
        elem.send_keys(Keys.CONTROL+"w")
        return
    
    def get_elements(self):
        xpaths = {}
        for obj in dir(self):
            try:
                xpaths[obj.name] = obj.xpath
            except AttributeError as err:
                pass
        return xpaths

