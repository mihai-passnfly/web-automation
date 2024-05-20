import json
import logging
import os
import random
from time import sleep
import logging
import requests
import unidecode
from furl import furl
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException, TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import base64
import re
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient import errors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import datetime
from collections import OrderedDict
import zipfile
import time

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class BaseSelenium:

    def __init__(self):
        self.driver_params = {}
        #run it locally
        #self.selenium_remote_host = 'http://automation-selenium:4444/wd/hub'
        self.use_headless = False
        self.logger =logging.getLogger(__name__)
        self.init_driver()

    def _init_options(self):

        self.logger.debug('Init Chrome options.')
        options = webdriver.ChromeOptions()
        if self.use_headless:
            options.add_argument('headless')
            options.add_argument('disable-gpu')
            options.add_argument('no-sandbox')


        options.add_argument('start-maximized')
        options.add_argument('profile-directory=Default')
        options.add_argument('--kiosk-printing')
        options.add_argument('--prompt-for-external-extensions')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--ignore-certificate-errors')

        return options

    def _get_driver(self, options):
        """
        # Remote execution
        self.driver_params['command_executor'] = self.selenium_remote_host
        self.driver_params['options'] = options
        self.driver_params['desired_capabilities'] = webdriver.DesiredCapabilities.CHROME
        return webdriver.Remote(**self.driver_params)
        """
        # Local execution
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(60)
            return driver
        except WebDriverException as e:
            self.logger.error('Error on getting Chrome driver locally: {}'.format(e))
            return None

    def open_url(self, url):


        try:

            self.driver.get(url)  

        except Exception as exc:
            raise exc




    def init_driver(self):
        """
        Options are set.
        """
        options = self._init_options()

        try:
            self.driver = self._get_driver(options)
            self.driver.set_page_load_timeout(60)

        except WebDriverException as e:
            self.logger.error('Error on running chrome driver, error exception:\n{}'.format(e))

    def close_driver(self):
        """
        Closes the driver.
        """
        try:
            self.driver.quit()
            self.logger.debug('Driver quit')

        except WebDriverException as e:
            message = str(e)
            self.logger.error('Failed closing the browser - {}'.format(message))

        except AttributeError as e:
            message = str(e)
            self.logger.error("Browser didn't initialized - {}".format(message))


    # --- TOOLS METHODS ---

    @staticmethod
    def random_sleep(_from=3.0, _to=5.5):
        """
        Waiting for the page to fully load before attempting next actions
        """
        sleep(random.uniform(_from, _to))

    @staticmethod
    def choose_type_selector(selector):
        """
        Determines the selector's type of path.
        :param selector: element's selector to be assessed
        :return: appropriate element selector by type
        """
        xpath_selector = selector.startswith('/') or selector.startswith('./')
        return By.XPATH if xpath_selector else By.CSS_SELECTOR

    # --- FIND METHODS ---

    def _find_element(self, selectors, scope=None, wait_seconds=0, ignore_exception=False, many=False, _format=None):
        """
        Searches and finds a html element with a given selector.
        :param selectors: list containing different possible paths to the element in the DOM.
        :param scope: html element in where to search the element.
        :param wait_seconds: timeout for finding the element.
        :param ignore_exception: if element not found and ignore_exception set to False, will raise NoSuchElementException; if set to True, will skip the exception and proceed.
        :param many: False, return first matching element; True, return a list of all the matching elements.
        :param _format: dict if selector's name need to be formatted
        :return: returns the WebElement found, if not found, returns None
        """
        if not scope:
            scope = self.driver

        element = None if not many else []
        if _format:
            selectors_copy = [selector.format(**_format) for selector in selectors]
        else:
            selectors_copy = selectors[:]  # Deep copy of the list

        selector = selectors_copy.pop(0)  # First element's selector has a timeout - html load time
        by = BaseSelenium.choose_type_selector(selector)
        try:
            if wait_seconds > 0:
                # Searching with timeout
                if many:
                    element = WebDriverWait(scope, wait_seconds).until(expected_conditions.presence_of_all_elements_located((by, selector)))
                else:
                    element = WebDriverWait(scope, wait_seconds).until(expected_conditions.presence_of_element_located((by, selector)))
            else:
                # Searching without timeout
                if many:
                    element = scope.find_elements(by, selector)
                else:
                    element = scope.find_element(by, selector)
        except WebDriverException:
            # If search failed, try with other paths found on the selectors list
            for selector in selectors_copy:
                by = BaseSelenium.choose_type_selector(selector)
                try:
                    if many:
                        element = scope.find_elements(by, selector)
                    else:
                        element = scope.find_element(by, selector)
                except NoSuchElementException:
                    pass

                if element:
                    # If element is found, break loop
                    break

        if not element and not ignore_exception:
            # If element couldn't be found an ignore_exception is False, raise an error
            raise WebDriverException(msg='[WARNING] Couldn\'t find: {} ***'.format(selector))

        if element and self.use_headless:
            if many and isinstance(element, list):
                destination_element = element[0]
            else:
                destination_element = element
            ActionChains(self.driver).move_to_element(destination_element).perform()

        return element

    def find_element(self, selectors, **kwargs):
        return self._find_element(selectors, **kwargs)

    def find_elements(self, selectors, **kwargs):
        kwargs['many'] = True
        return self._find_element(selectors, **kwargs)

    def find_element_with_text(self,selectors,**kwargs):

        text = None
        retry = 2

        for i in range(retry):
            element = self.find_element(selectors,**kwargs)
            text = element.text
            if text:
                return text
            time.sleep(5)

        raise Exception('Element not found')





    # --- FILL METHODS ---

    def fill_input(self, selectors, value, **kwargs):
        """
        Finds and fills an input-type element with a given value.
        """
        slowmo = kwargs.pop('slowmo', False)
        element = self.find_element(selectors, **kwargs)
        if element:
            self.fill_element(element, value, slowmo=slowmo)

            self.logger.debug('Input filled: {}'.format(selectors))
        return element

    def fill_empty_input(self, selectors, value, **kwargs):
        slowmo = kwargs.pop('slowmo', False)
        input_element = self.find_element(selectors, ignore_exception=True, **kwargs)
        if input_element and input_element.is_displayed() and input_element.get_attribute('value') == '':
            return self.fill_element(input_element, value, slowmo=slowmo)

    def fill_empty_input_element(self, element, value, **kwargs):
        slowmo = kwargs.pop('slowmo', False)
        input_element = element
        if input_element and input_element.is_displayed() and input_element.get_attribute('value') == '':
            return self.fill_element(input_element, value, slowmo=slowmo)

    def fill_element(self, element, value, slowmo=False):
        """
        Fills an input-type element with a given value.
        """
        element.clear()
        if slowmo:
            self.random_sleep()
            for character in value:
                element.send_keys(character)
                self.random_sleep(0.3, 0.5)
        else:
            element.send_keys(value)
        return element

    def is_element_disabled(self, element):
        return self.driver.execute_script("return arguments[0].disabled", element)

    def _fill_select(self, select, value=None, index=None, text=None):
        if value:
            select.select_by_value(value)
        if index is not None:
            select.select_by_index(index)
        if text:
            try:
                select.select_by_visible_text(text)
            except NoSuchElementException as e:
                list_values = [opt.text for opt in select.options]
                best_match = automation_utils.extract_best(text, list_values)
                select.options[best_match[1]].click()

    def fill_select_element(self, select, value=None, index=None, text=None):
        self._fill_select(select, value, index, text)

    def fill_select(self, selectors, value=None, index=None, text=None, **kwargs):
        """
        Finds and fills a select-type element with a given value or with a given index.
        :param value: select by matching value
        :param index: select by matching index
        :param text: select by matching text
        """
        element = self.find_element(selectors, **kwargs)
        if element:
            select = Select(element)
            self._fill_select(select, value, index, text)

            self.logger.debug('Selected: {}'.format(selectors))

        sleep(0.5)
        return element

    def fill_empty_select(self, selectors, value=None, index=None, text=None, **kwargs):
        select_element = self.find_element(selectors, **kwargs)
        if select_element:
            select = Select(select_element)
            try:
                if select.first_selected_option == select.options[0]:
                    return self.fill_select_element(select, value=value, index=index, text=text)
            except NoSuchElementException:  # No options selected
                return self.fill_select_element(select, value=value, index=index, text=text)
        return None

    def is_empty_select(self, selectors, **kwargs):
        select_element = self.find_element(selectors, **kwargs)
        if select_element:
            select = Select(select_element)
            try:
                if select.first_selected_option == select.options[0]:
                    return select
            except NoSuchElementException:  # No options selected
                return select
        return None

    # --- CLICK METHODS ---

    def click(self, selectors, **kwargs):
        """
        Finds and clicks on a clickable element.
        """
        element = self.find_element(selectors, **kwargs)
        if element:
            element.click()

            self.logger.debug('Clicked: {}'.format(selectors))

        return element

    def click_force_js(self, selectors, **kwargs):
        """
        Finds and tries normal click. If selenium click is not working, tries JS click.
        """
        element = self.find_element(selectors, **kwargs)
        if element:
            try:
                element.click()
                self.logger.debug('Clicked: {}'.format(selectors))
            except:
                self.driver.execute_script("arguments[0].click();", element)
                self.logger.debug('Clicked(JS): {}'.format(selectors))

        return element


    def click_parent(self, selectors, **kwargs):
        """
        Finds and clicks on a clickable parent element.
        """
        element = self.find_element(selectors, **kwargs)
        if element:
            element = self.get_parent_element(element)
            element.click()

            self.logger.debug('Clicked: {}'.format(selectors))

        return element

    def click_displayed(self, selectors, **kwargs):
        """
        Finds and clicks on a clickable element.
        """
        element = self.find_element(selectors, **kwargs)
        if element and element.is_displayed():
            element.click()

            self.logger.debug('Clicked: {}'.format(selectors))

            return element

        return None

    def uncheck(self, selectors, **kwargs):
        element = self.find_element(selectors, **kwargs)
        if element and element.is_selected():
            element.click()

    def remove_dom(self, selectors, **kwargs):
        """
        Finds and clicks on a clickable element.
        """
        element = self.find_element(selectors, **kwargs)
        if element:
            self.driver.execute_script("return arguments[0].remove()", element)

        return element

    # --- SWITCH METHODS ---

    def bind_iframe(self, selectors, **kwargs):
        element = self.find_element(selectors, **kwargs)
        if element:
            self.driver.switch_to_frame(element)
        return element

    def switch_new_tab(self, tab_index=1):
        if len(self.driver.window_handles) > 1:
            self.driver.switch_to_window(self.driver.window_handles[tab_index])
            return True
        return False

    # --- MOVE TO METHODS ---

    def move_to(self, selectors, **kwargs):
        element = self.find_element(selectors, **kwargs)
        if element:
            self.move_to_element(element)
        return element

    def move_to_element(self, element):
        ActionChains(self.driver).move_to_element(element).perform()
        sleep(1)

    def scroll_to_object(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)

    def center_screen_on_element(self, element):
        scrollElementIntoMiddle = """var viewPortHeight = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
        var elementTop = arguments[0].getBoundingClientRect().top
        window.scrollBy(0, elementTop-(viewPortHeight/2));"""
        self.driver.execute_script(scrollElementIntoMiddle, element)

    # --- GMAIL METHODS ---
    def ListMessagesMatchingQuery(self, service, user_id, query=''):

        try:
            response = service.users().messages().list(userId=user_id,
                                                    q=query).execute()
            messages = []
            if 'messages' in response:
                messages.extend(response['messages'])

            while 'nextPageToken' in response:
                page_token = response['nextPageToken']
                response = service.users().messages().list(userId=user_id, q=query,
                                                    pageToken=page_token).execute()
                messages.extend(response['messages'])

            return messages
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def GetMessage(self, service, user_id, msg_id):
        try:
            message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
            testResponse = message["payload"]["parts"][1]
            base64MessageBody = testResponse["body"]["data"]
            msg_str = base64.urlsafe_b64decode(base64MessageBody)
            return msg_str.decode('utf-8')

        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def get_email_verification(self, emailWithID):
        self.random_sleep(4.5, 8.5)
        # Get Creds for Gmail
        store = file.Storage('/var/app/current/app/automation/engines/token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('/var/app/current/app/automation/engines/credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('gmail', 'v1', http=creds.authorize(Http()))
        # Use this once plus check has been removed from email input on fasttrack.flights
        emailToSearchFor = "'to:" + emailWithID + "'"
        print(emailToSearchFor)
        # emailToSearchFor = "'from:" + "verify@fasttrack.flights'"
        messageList = self.ListMessagesMatchingQuery(service, 'me', emailToSearchFor)
        body = self.GetMessage(service, 'me', messageList[0]['id'])
        pattern = r'<div class="codes-container">\s+(\d+)\s+</div>'
        otpCode = re.search(pattern, body)
        if otpCode:
            found = otpCode.group(1)
            return found
        else:
            raise Exception("Unable to get the OTP code")

    def get_venice_registration(self, emailWithID):
        self.random_sleep(7.5, 12.5)
        # Get Creds for Gmail
        store = file.Storage('/var/app/current/app/automation/engines/token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('/var/app/current/app/automation/engines/credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('gmail', 'v1', http=creds.authorize(Http()))
        emailToSearchFor = "'to:" + emailWithID + "'"
        messageList = self.ListMessagesMatchingQuery(service, 'me', emailToSearchFor)
        body = self.GetMessage(service, 'me', messageList[0]['id'])
        pattern = r'<a\s+href=[\'"](https://[^\'"]*registrationaccomplished[^\'"]*)[\'"]>'
        link = re.search(pattern, body)
        if link:
            found = link.group(1)
            return found
        else:
            raise Exception("Unable to get the registration link")
        
    def send_email(self, airport, traceback, messageToSend):
        message = MIMEMultipart()
        message["To"] = 'jesse.balfe@sast-mfa.com'
        message["From"] = 'fttesttracker@gmail.com'
        message["Subject"] = 'Error with: ' + airport
        errorMessage = messageToSend + '\n\n' + traceback
        messageText = MIMEText(errorMessage, 'plain')        
        message.attach(messageText)

        email = 'fttesttracker@gmail.com'
        password = 'sqcp hget nyyi naym'

        server = smtplib.SMTP('smtp.gmail.com:587')
        server.ehlo('Gmail')
        server.starttls()
        server.login(email,password)
        fromaddr = 'fttesttracker@gmail.com'
        toaddrs  = 'fasttrackotpcheck@gmail.com'
        server.sendmail(fromaddr,toaddrs,message.as_string())
        server.quit()    

    # --- OTHER METHODS ---

    def empty_input(self, selectors, **kwargs):
        element = self.find_element(selectors, **kwargs)
        if element and element.get_attribute('value') == '':
            return element
        return None

    def get_parent_element(self, element, levels=1):
        xpath = '/'.join(['..'] * levels)
        return element.find_element_by_xpath(xpath)

    def wait_loader(self, selectors, sleep_seconds=1, max_retries=-1):
        """
        :param selectors: list
        :param sleep_seconds: int
        :param max_retries: int positive number
        :return:
        """
        try:
            loader = self.find_element(selectors, ignore_exception=True)
            while loader and loader.is_displayed() and max_retries:
                self.logger.debug('Found: {}. Remaining time: {}'.format(selectors, f'{sleep_seconds * max_retries} seconds' if max_retries > 0 else 'infinite'))
                sleep(sleep_seconds)
                max_retries -= 1
                loader = self.find_element(selectors, ignore_exception=True)
        except StaleElementReferenceException:
            loader = None

    def check_error(self, selectors, scope=None):
        element = self.find_element(selectors, wait_seconds=self.wait_seconds, scope=scope, ignore_exception=True)
        if element and element.is_displayed() and element.text != '':
            return unidecode.unidecode(element.text)
        return None

    def check_several_error(self, selectors, scope=None):
        """
        Sometimes there are several elements matching with the selectors.
        The method self.check_error above will select only the first one, and return None if it is not displayed.
        This method tests every elements matching with the selectors and returns the text of the first displayed one.
        It is very useful at some moments, especially with the APIS
        """
        potential_errors = [element for selector in selectors for element in self.find_elements([selector], ignore_exception=True, scope=scope)]
        errors = [error for error in potential_errors if error.is_displayed() and error.text != '']
        if errors:
            error = errors[0]
            return unidecode.unidecode(error.text)

        return None

    def force_element_visible(self, element):
        self.driver.execute_script("arguments[0].setAttribute('style', 'visibility:visible;z-index:99999;')", element)

    def override_link_to_open_in_same_tab(self, element):
        """
        By changing target="_blank" to target=""
        """
        self.driver.execute_script("arguments[0].setAttribute('target', '')", element)