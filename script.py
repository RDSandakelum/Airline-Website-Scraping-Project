from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import TimeoutException
import json
from datetime import datetime
from datetime import datetime, timedelta
import re

class DatesCal:
    def departure_date_format(self, date):
        date_object = datetime.strptime(date, "%a, %d %b %Y")
        formatted_date_string = date_object.strftime("%Y-%m-%d")
        return formatted_date_string
    
    def next_date_cal(self, departure_date_string, air_time):
        date_object = datetime.strptime(departure_date_string, "%Y-%m-%d").date()

        hour_search = re.search(r'(\d+)h', air_time)
        minute_search = re.search(r'(\d+)m', air_time)

        hours = int(hour_search.group(1)) if hour_search else 0
        minutes = int(minute_search.group(1)) if minute_search else 0

        arival_date_object = date_object + timedelta(hours=hours, minutes=minutes)
        formatted_arival_date_string = arival_date_object.strftime("%Y-%m-%d")
        return formatted_arival_date_string
    
    def next_time_cal(self, departure_time_string, air_time):
        time_object = datetime.strptime(departure_time_string, "%H:%M").time()

        hour_search = re.search(r'(\d+)h', air_time)
        minute_search = re.search(r'(\d+)m', air_time)

        hours = int(hour_search.group(1)) if hour_search else 0
        minutes = int(minute_search.group(1)) if minute_search else 0

        current_datetime = datetime.now()
        time_with_date_object = datetime.combine(current_datetime, time_object)

        arrival_datetime_object = time_with_date_object + timedelta(hours=hours, minutes=minutes)
        formatted_arrival_time_string = arrival_datetime_object.time().strftime("%H:%M")
        return formatted_arrival_time_string
    
class AirlineMapping:

    def __init__(self):
        # if os.environ.get('IS_EXECUTING_LAMBDA') == '1':
        # json_mapping_file='/opt/python/airline_mapping.json'
        # else:
        json_mapping_file='airline_mapping-1.json'

        with open(json_mapping_file) as json_file:
            self.airline_mapping = json.load(json_file)

    def get_airline_code_from_flight_number(self, flight_number):
        try:
            iata_code = flight_number[0:2]
            return self.get_airline_code_from_iata_code(iata_code)
        except:
            return flight_number

    def get_airline_code_from_iata_code(self, airline_iata_code):
        try:
            return self.airline_mapping[airline_iata_code]
        except Exception as e:
            return airline_iata_code

class FlightClass:
    def classFind(self,className):
        if className == "ECONOMY":
            return "Y"
        elif className == "PREMIUM ECONOMY":
            return "W"
        elif className == "BUSINESS":
            return "C"
        elif className == "FIRST":
            return "F"

class CommonData:
    def miles(self,flight):
        points_total = flight.find_element(By.CLASS_NAME, "price-container").find_element(By.XPATH, ".//span[contains(text(), 'K')]").text.split("K")[0]
        if "."  in points_total:
            points = points_total.split(".")
            points_f = points[0]+points[1]
            return points_f+"0"*(3-len(points[1]))
        else:
            points_f = points_total
            return points_f+"000"
    
    def tax(self,flight):
        cash_container = flight.find_element(By.CLASS_NAME, "remaining-cash").find_elements(By.CLASS_NAME, "ng-star-inserted")
        tax_container = cash_container[2].text.split(" ")
        tax = {}
        tax["amount"] = tax_container[1][1:]
        if tax_container[0] == "CA":
            tax["currency"] = "CAD"
        else:
            tax["currency"] = tax_container[0]
        return tax

    def flight_class(self,flight):
        available = flight.find_element(By.CLASS_NAME, "available-cabin")
        available_class = available.get_attribute("aria-label").split("Class")[0].strip()
        flight_class = FlightClass()
        return flight_class.classFind(available_class.upper())

    def more_details_tab(self,flight):
        wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "detail-link")))
        flight.find_element(By.CLASS_NAME, "detail-link").click()
        
chrome_options = Options()
chrome_options.add_argument("--profile-directory=Profile 2")
chrome_options.add_argument('--remote-debugging-port=9222')
chrome_options.add_experimental_option('debuggerAddress', 'localhost:9222')

driver = webdriver.Chrome(options=chrome_options)

driver.get('https://www.aircanada.com/aeroplan/redeem/availability/outbound?tripType=O&org0=TYO&dest0=AXT&departureDate0=2023-06-09&ADT=1&YTH=0&CHD=0&INF=0&INS=0')

output = {"direct_flights":[], "transit_flights": []}
wait = WebDriverWait(driver, 100)

try:
    element = WebDriverWait(driver,40).until(
        EC.presence_of_element_located((By.CLASS_NAME, "icon-close")))
    element.click()
except:
    pass


try:
    wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "upsell-row")))

    flights = driver.find_elements(By.CLASS_NAME, "upsell-row")
    
    direct_flights = []
    transit_flights = []

    for flight in flights:
        flight_details =  {}
        img = flight.find_elements(By.TAG_NAME, "img")
        common_data = CommonData()
        if(len(img) == 1):
            airline_text_div = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "details-row")))
            airline_text = airline_text_div.find_element(By.CLASS_NAME, "ng-star-inserted")
            flight_details["operating_company"] = airline_text.text.split("by")[1].strip()

            departure_time = flight.find_element(By.CLASS_NAME, "departure-time").text 
            flight_details["departure_time"] = departure_time.strip()

            arival_time = flight.find_element(By.CLASS_NAME, "arrival-time").text 
            flight_details["arrival_time"] = arival_time.strip()

            flight_details["mile"] = common_data.miles(flight)

            flight_details["tax"] = common_data.tax(flight)

            flight_details["class"] = common_data.flight_class(flight)

            try:
                flight_details["seat_status"] = flight.find_element(By.CLASS_NAME, "seat-text").text.split(" ")[0].strip()
            except:
                flight_details["seat_status"] = "Av"

            
            common_data.more_details_tab(flight)

            try:
                element = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "lightbox-container")))
                
                dates_cal = DatesCal()
                departure_date = dates_cal.departure_date_format(element.find_element(By.CLASS_NAME, "head").text.split("Departing ")[1])
                flight_details["departure_date"] = departure_date

                airTime = element.find_element(By.CSS_SELECTOR, "span.body").text.split(":")[1].strip()
                flight_details["arrival_date"] = dates_cal.next_date_cal(departure_date, airTime)

                
                flight_number = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "flight-number"))).text.strip()
                flight_details["flight_number"] = flight_number
                map = AirlineMapping()
                code = map.get_airline_code_from_flight_number(flight_number)
                flight_details["airline_company_code"] = code

                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "icon-close"))).click()

            except TimeoutException:
                print("Timeout occurred") 
            
            flight_details = {k: flight_details[k] for k in sorted(flight_details)}

            direct_flights.append(flight_details)

        elif (len(img)>1):
            time.sleep(1)
            
            flight_details["mile"] = common_data.miles(flight)

            flight_details["tax"] = common_data.tax(flight)

            class_s = common_data.flight_class(flight)

            try:
                flight_details["seat_status"] = flight.find_element(By.CLASS_NAME, "seat-text").text.split(" ")[0].strip()
            except:
                flight_details["seat_status"] = "Av"

            common_data.more_details_tab(flight)

            try:
                element = wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "lightbox-container")))
                
                dates_cal = DatesCal()
                departure_date = dates_cal.departure_date_format(element.find_element(By.CLASS_NAME, "head").text.split("Departing ")[1])

                transits_inf = element.find_elements(By.CLASS_NAME, "container")
                transit_list = []
                airTimes = element.find_elements(By.XPATH, ".//span[starts-with(text(), ' Duration:')]")
                layover_times = element.find_elements(By.XPATH, ".//span[contains(text(), 'Layover') or contains(text(), 'layover')]")

                for i in range(0, len(transits_inf)):
                    if i % 2 == 0:
                        flight = {}

                        flight["class"] = class_s
                        departure_time = transits_inf[i].find_element(By.CSS_SELECTOR, "span.mat-subheading-1").text.strip()
                        flight["departure_time"] = departure_time

                        if i == 0:
                            flight["departure_date"] = departure_date
                            flight["arrival_date"] = dates_cal.next_date_cal(departure_date, airTimes[i].text.split(":")[1].strip())
                            flight["arrival_time"] = dates_cal.next_time_cal(departure_time, airTimes[i].text.split(":")[1].strip())

                        else:
                        
                            lst = layover_times[i-(int(i/2)+1)].text.split(" ")
                        
                            for b in (lst):
                                if any(character.isdigit() for character in b):
                                    index = lst.index(b)

                            departure_date = dates_cal.next_date_cal(transit_list[len(transit_list)-1]["arrival_date"], lst[index])
                            flight["departure_date"] = departure_date
                            flight["arrival_date"] = dates_cal.next_date_cal(departure_date, airTimes[i-int(i/2)].text.split(":")[1].strip())
                            flight["arrival_time"] = dates_cal.next_time_cal(departure_time, airTimes[i-int(i/2)].text.split(":")[1].strip())


                        flight_number = transits_inf[i].find_element(By.CLASS_NAME, "flight-number").text.strip()
                        flight["flight_number"] = flight_number

                        map = AirlineMapping()
                        code = map.get_airline_code_from_flight_number(flight_number)
                        flight["airline_company_code"] = code

                        company_span = transits_inf[i].find_element(By.CLASS_NAME, "airline-details").find_element(By.XPATH, ".//span[starts-with(text(), ' | Operated')]")
                        flight["operating_company"] = company_span.text.split("by")[1].strip()

                        flight["departure_airport_code"] = transits_inf[i].find_element(By.CLASS_NAME, "font-weight-light").text.split(" ")[1].strip()
                    
                        flight = {k: flight[k] for k in sorted(flight)}
                        transit_list.append(flight)

                    else:
                        transit_list[-1]["arrival_airport_code"] = transits_inf[i].find_element(By.CLASS_NAME, "font-weight-light").text.split(" ")[1].strip()
                    
                flight_details["transit"] =  transit_list
                

                wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "icon-close"))).click()
            except TimeoutException:
                print("Timeout occurred") 
            
            flight_details = {k: flight_details[k] for k in sorted(flight_details)}

            transit_flights.append(flight_details)


    output["direct_flights"] = direct_flights
    output["transit_flights"]  = transit_flights
    with open('flights.json', 'w') as json_file:
        json.dump(output, json_file, indent=4)
    print(output)

except TimeoutError:
    print("Timeout error")
