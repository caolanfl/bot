import time
import random
import csv
import re
from scrapy.selector import Selector
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from python_anticaptcha import AnticaptchaClient, NoCaptchaTaskProxylessTask

class YoutubeCrawler():

    def __init__(self):
        chrome_options = Options()
        #chrome_options.add_argument("--headless")
        #chrome_options.add_argument('--proxy-server=%s' % '192.161.166.122:3128')
        chrome_options.add_argument("--window-size=1920x1080")

        path_to_chromedriver = 'chromedriver'
        self.driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=path_to_chromedriver)

    def crawl(self, depth, keyword):

        with open(r'youtube.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['keyword', 'user/channel'])

        # 2d array of channels in form [ [keyword, url] ]
        user_channels = []
        keyword = keyword.strip()
        print("keyword [{}]".format(keyword))
        driver = self.driver
        driver.get('https://www.youtube.com/results?search_query={}'.format(keyword))

        # Searching for only channels
        filter_btn = driver.find_elements_by_xpath(".//paper-button[contains(@aria-label, 'Search filters')]")[0]
        filter_btn.click()
        time.sleep(1)
        channel_btn = driver.find_elements_by_xpath(".//div[contains(@title, 'Search for Channel')]")[0]
        channel_btn = channel_btn.find_element_by_xpath('..')
        channel_btn.click()
        time.sleep(1)
        
        for i in range(depth):
            print(i)
            html = driver.find_element_by_tag_name('html')
            html.send_keys(Keys.PAGE_DOWN)
            html.send_keys(Keys.PAGE_DOWN)
            time.sleep(random.uniform(0.5, 1.5))

        response = Selector(text=str(driver.page_source))
        index = 0
        for r in response.xpath("//*[contains(@class, 'ytd-item-section-renderer')]"):
            user = r.xpath(".//a[contains(@href, '/user/')]/@href").extract_first()
            channel = r.xpath(".//a[contains(@href, '/channel/')]/@href").extract_first()
            user_channel = None
            if user:
                user = 'https://www.youtube.com' + user
                user_channel = user

            if channel:
                channel = 'https://www.youtube.com' + channel
                user_channel = channel

            if user_channel:
                if [keyword,user_channel] not in user_channels:
                    user_channels.append([keyword,user_channel])
                            
                with open(r'youtube.csv', 'a', newline='',  encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=';')
                    if index == 0:
                        writer.writerow([keyword, user_channel])
                    else:
                        writer.writerow([None, user_channel])
                index += 1
                    
        print(len(user_channels))
        num_visited = 0
        for user_channel in user_channels:
            print('Collected : ' + str(num_visited))
            keyword = user_channel[0]
            channel_url = user_channel[1]
                
            driver = self.driver
            driver.get(channel_url+'/about')
            response = Selector(text=str(driver.page_source))

            # Check if email in description
            emails = []
            desc = driver.find_elements_by_css_selector("div#description-container > yt-formatted-string#description")
            if desc:
                emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", desc[0].text)
                if emails:
                    email = ', '.join(emails)

            # If email not in description solve captcha for it   
            if not emails: 
                if len(driver.find_elements_by_xpath(".//paper-button[contains(@aria-label, 'View email address')]")) > 0:
                    # Pressing show email button
                    show_email_btn = driver.find_elements_by_xpath(".//paper-button[contains(@aria-label, 'View email address')]")[0]
                    show_email_btn.click()
                    time.sleep(2)

                    # Extracting recaptcha site_key
                    response = Selector(text=str(driver.page_source))
                    recaptcha_site_key = response.xpath(".//div[contains(@class, 'g-recaptcha')]/@data-sitekey").extract_first()
                    anticaptcha_api_key = '95887acbc0f0e94f3282b0c372983600'

                    # Scrolling down so captcha is in view(suspicious otherwise)
                    html = driver.find_element_by_tag_name('html')
                    html.send_keys(Keys.PAGE_DOWN)
                    time.sleep(random.randint(1, 3))

                    # Solving recapthca
                    client = AnticaptchaClient(anticaptcha_api_key)
                    task = NoCaptchaTaskProxylessTask(channel_url+'/about', recaptcha_site_key)
                    job = client.createTask(task)
                    job.join()
                    solution = job.get_solution_response()
                    driver.execute_script('document.getElementById("g-recaptcha-response").innerHTML = "%s"' % solution)

                    # Wait a moment to execute the script (just in case).
                    time.sleep(1)

                    # Press submit button
                    driver.find_element_by_xpath("//button[contains(@class, 'captcha-submit')]").click()
                    time.sleep(1)

                    response = Selector(text=str(driver.page_source))
                    email = response.xpath(".//a[contains(@href, 'mailto:')]/@href").extract_first()[7:]
                else:
                    email = 'NONE'

            with open(r'emails'+keyword+'.csv', 'a', newline='',  encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([keyword, channel_url, email])

            print(email)
            num_visited += 1


if __name__ == '__main__':
    try:
        depth = 3
        keyword = input('Keyword : ')
        crawler = YoutubeCrawler()
        crawler.crawl(depth, keyword)
    finally:
        crawler.driver.quit()
