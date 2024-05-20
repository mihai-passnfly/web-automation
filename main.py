import sys
import traceback
from selenium.webdriver.common.by import By
import uuid
import time
import yaml
from base import BaseSelenium

class Website(BaseSelenium):
    def __init__(self):
        BaseSelenium.__init__(self)
        print("I have been instantiated")

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            return yaml.safe_load(file)

    def accept_cookies(self):
        try:
            self.click(['#ccc-overlay'], wait_seconds=10)
            self.click(['#ccc-notify'], wait_seconds=5)
            self.click(['#ccc-notify-reject'], wait_seconds=5)
            time.sleep(1)
        except:
            pass
            
    def proceed_to_payment(self):
        self.click_force_js(["//*[contains(text(),'Book')]"], wait_seconds=8)

    def enter_personal_details(self, first_name, last_name, emailWithID, postCode, address, phoneNumber):
        self.click(['a[href="/booking/checkout"]'], wait_seconds=10)
        self.fill_input(['#FirstName'], first_name, wait_seconds=10)
        self.fill_input(['#LastName'], last_name)
        self.fill_input(['#HouseNameNumber'], address)
        self.fill_input(['#Postcode'], postCode)
        self.fill_input(['#ContactNumber'], phoneNumber)
        self.fill_input(['#EmailAddress'], emailWithID)
        self.click_force_js(['#TermsAndConditions'], wait_seconds=10)
        self.click_force_js(['#formSubmitBtn'], wait_seconds=10)


    def make_payment(self, card_number, expiry_month, expiry_year, cvv):
        self.fill_input(['#ekashu_card_number'], card_number, wait_seconds=10)
        self.fill_input(['#ekashu_verification_value'], cvv, wait_seconds=10)
        self.fill_select(['#ekashu_input_expires_end_month'], value=str(expiry_month))
        self.fill_select(['#ekashu_input_expires_end_year'], value=str(expiry_year))
        self.click_force_js(['#ekashu_submit_continue_button'], wait_seconds=10)

    def run(self):
        airport_config = self.load_config('/var/app/current/app/automation/engines/newcastle_config.yml')
        number_of_passes = airport_config['number_of_passes']
        first_name = airport_config['first_name']
        last_name = airport_config['last_name']
        card_number = airport_config['card_number']
        expiry_month = airport_config['expiry_month']
        expiry_year = airport_config['expiry_year_short']
        address = airport_config['address']
        postcode = airport_config['postcode']
        phoneNumber = airport_config['phone']
        cvv = airport_config['cvv']
        dateOfFlight = airport_config['date_of_flight']
        checkInTime = airport_config['check_in_time']

        emailIdentifer = uuid.uuid4().hex
        emailWithID = "fasttrackotpcheck+" + emailIdentifer + "@gmail.com"
        try:
            self.open_url('https://www.newcastleairport.com/booking/fast-track-results?date=' + str(dateOfFlight) + '&time=' + str(checkInTime) + '&passengers=' + str(number_of_passes))
            self.accept_cookies()
            self.proceed_to_payment()
            self.enter_personal_details(first_name, last_name, emailWithID, postcode, address, phoneNumber)
            self.make_payment(card_number, expiry_month, expiry_year, cvv)
            print('payment completed')
            time.sleep(10)
            self.close_driver()
        except Exception as error:
            # Capture traceback information
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_info = traceback.extract_tb(exc_traceback)
            stacktraceToSend = str(tb_info)
            self.send_email('Newcastle', stacktraceToSend, str(error))
        pass

if __name__ == "__main__":
    # Create an instance of the Website class
    website = Website()

    # Call the run method
    website.run()
