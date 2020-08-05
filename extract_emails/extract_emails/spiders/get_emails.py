# -*- coding: utf-8 -*-
import json
import pandas as pd
import PyPDF2
import re
import requests
import scrapy
import time

from scrapy.http import Request
from scrapy.selector import Selector


class GetEmailsSpider(scrapy.Spider):
    name = 'get_emails'
    headers = {
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'x-client-data': 'CIi2yQEIo7bJAQjBtskBCKmdygEIjqzKAQiGtcoBCP68ygEI58jKAQi0y8oB',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-US,en;q=0.9',
    }
    dom_detailer_api_key = '5SUT34180BBFG'

    def __init__(self, *args, **kwargs):
        self.urls = []
        self.email_addresses = []

        # Read the input CSV file & fillup the self.urls list
        # csv_files = ['technology.csv', 'softwarereview.csv', 'dogtraining.csv', 'fitnesstips.csv']
        csv_data = pd.read_csv('./extract_emails/technology.csv')
        # csv_data = pd.read_csv('softwarereview.csv')
        # csv_data = pd.read_csv('dogtraining.csv')
        # csv_data = pd.read_csv('fitnesstips.csv')
        # csv_data = pd.read_csv('pets.csv')
        # csv_data = pd.read_csv(input_file)
        # for csv_file in csv_files:
        #     csv_data = pd.read_csv(csv_file)
        for url in csv_data['website_url']:
            self.urls.append(url.strip())
        
        # Open an HTTP session for google.com and set cookies
        self.session = requests.Session()
        self.session.get('https://www.google.com/search', headers=self.headers,)
        self.cookie = self._get_cookie()
        self.headers.update({'cookie': self.cookie})

    def _get_cookie(self):
        cookies = []
        for key, value in self.session.cookies.get_dict().items():
            cookies.append('%s=%s' % (key, value))
        cookie = "; ".join(cookies)
        print('[INFO]  Cookie: %s' % cookie)
        return cookie

    def start_requests(self):
        # Access each URL in the self.urls list
        for url in self.urls:
            domain = url.split('/')[2].replace('www.', '')
            yield Request(url, callback=self.parse, headers=self.headers, meta={'dont_proxy': True, 'domain': domain})

    def parse(self, response):
        try:
            body = response.text
        except:
            if response.body:
                body = response.body.decode("utf-8", errors="ignore")
                if body.startswith('%PDF'):
                    body = self._read_pdf(response.body)

        # Parse website reponse
        self.email_addresses = []
        domain = response.meta['domain']

        # Find email addresses of the form user@domain.root
        if re.search(r"[a-z0-9\.\-+_]+\@[a-z0-9\.\-+_]+\.[a-z]+", body):
            email = re.search(r"([a-z0-9\.\-+_]+\@[a-z0-9\.\-+_]+\.[a-z]+)", body).group(1)
            # self._filter_emails(emails)
            self._filter_emails(email)

        # Find email addresses of the form user<SPACES>@<SPACES>domain.root
        if re.search(r"[a-z0-9\.\-+_]+\s+?\@\s+?[a-z0-9\.\-+_]+\.[a-z]+", body):
            email = re.search(r"([a-z0-9\.\-+_]+\s+?\@\s+?[a-z0-9\.\-+_]+\.[a-z]+)", body).group(1)
            # self._filter_emails(emails)
            self._filter_emails(email)

        # Find email addresses of the form user [at] domain [dot] root
        if re.search(r'\[at\].*\[dot\]', body):
            resp = re.sub(r'\s+\[at\]\s+', '@', body)
            resp = re.sub(r'\s+\[dot\]\s+', '.', resp)
            email = re.search(r"([a-z0-9\.\-+_]+\@[a-z0-9\.\-+_]+\.[a-z]+)", body)
            # self._filter_emails(emails)
            if email:
                self._filter_emails(email.group(1))

        # Find email addresses of the form user (at) domain (dot) root
        if re.search(r'\(at\).*dot', body, re.I):
            resp = re.sub(r'\s+\(at\)\s+', '@', body)
            resp = re.sub(r'\s+DOT\s+', '.', resp, re.I)
            email = re.search(r"([a-z0-9\.\-+_]+\@[a-z0-9\.\-+_]+\.[a-z]+)", body)
            # self._filter_emails(emails)
            if email:
                self._filter_emails(email.group(1))

        if self.email_addresses:
            # If email addresses are found then yield URL & email addresses
            unique_emails = list(dict.fromkeys(
                [x.lower() for x in self.email_addresses]))
            self.email_addresses = []
            yield Request(
                f'http://domdetailer.com/api/checkDomain.php?domain={domain}&app=DomDetailer&apikey={self.dom_detailer_api_key}&majesticChoice=root',
                headers=self.headers,
                callback=self.parse_dom_details,
                meta={
                    'dont_proxy': True,
                    'url': response.url,
                    'domain': domain,
                    'email': unique_emails[0] if unique_emails else 'NA',
                }
            )
        else:
            # Else access the URL and check if encoded emails are present.
            # If encoded emails found then decode the emails and yield
            yield Request(
                response.url,
                headers=self.headers,
                callback=self.parse_encoded_email,
                dont_filter=True,
                meta={
                    'dont_proxy': True,
                    'url': response.url,
                    'domain': domain,
                }
            )

            # If encoded emails are not found then search for emails in google and yield found emails
            # Search query example - site:techristic.com "@techristic.com" contact us
            if not self.email_addresses:
                domain = response.url.split('/')[2].replace('www.', '')
                url = f'https://www.google.com/search?q=site%3A{domain}+%22%40{domain}%22+contact+us&rlz=1C1GCEA_enIN901IN901&oq=site%3A{domain}+%22%40{domain}%22+contact+us&aqs=chrome..69i57j69i58.4168j0j7&sourceid=chrome&ie=UTF-8'
                headers = self.headers.copy()
                headers.update({'authority': 'www.google.com', 'X-Crawlera-Max-Retries': 0})
                yield Request(
                    url,
                    headers=headers,
                    callback=self.parse_google_search,
                    dont_filter=True,
                    meta={
                        'url': response.url,
                        'domain': domain,
                    }
                )

    # Method to parse encoded email addresses
    # Emails will have a class of __cf_email__.
    # Modify this method if you find any other xpath or css
    def parse_encoded_email(self, response):
        encoded_emails = []
        try:
            body = response.text
        except:
            if response.body:
                body = response.body.decode("utf-8", errors="ignore")
        resp = Selector(text=body)
        
        if resp.xpath('//span[@class="__cf_email__"]/@data-cfemail'):
            encoded_emails = resp.xpath(
                '//span[@class="__cf_email__"]/@data-cfemail').getall()

        if encoded_emails:
            for encoded_email in encoded_emails:
                if encoded_email:
                    decoded_email = ""
                    k = int(encoded_email[:2], 16)
                    for i in range(2, len(encoded_email)-1, 2):
                        decoded_email += chr(int(encoded_email[i:i+2], 16) ^ k)

                    if decoded_email and not decoded_email.startswith('@'):
                        (user, domain) = decoded_email.split('@')
                        if len(domain.split('.')) != 1 and not re.match(r'\d+', domain.split('.')[-1]):
                            decoded_email = decoded_email.strip('-').strip('.')
                            decoded_email = re.sub(r'\s+|\[|\]', '', decoded_email)
                            self.email_addresses.append(decoded_email)
                    else:
                        print(f'ERROR: Decoded Email not found - {response.url}')
            unique_emails = list(dict.fromkeys([x.lower() for x in self.email_addresses]))
            yield Request(
                f'http://domdetailer.com/api/checkDomain.php?domain={response.meta["domain"]}&app=DomDetailer&apikey={self.dom_detailer_api_key}&majesticChoice=root',
                headers=self.headers,
                callback=self.parse_dom_details,
                meta={
                    'dont_proxy': True,
                    'url': response.meta['url'],
                    'domain': response.meta['domain'],
                    'email': unique_emails[0] if unique_emails else 'NA',
                }
            )
        else:
            self.email_addresses = []

    # Method to parse google search results
    # Each google search results will be stored under a span of class "st"
    # Modify this method to enhance google search results.
    def parse_google_search(self, response):
        email_addresses = []
        # domain = response.meta['url'].split('/')[2].replace('www.', '')
        domain = response.meta['domain']
        try:
            body = response.text
        except:
            if response.body:
                body = response.body.decode("utf-8", errors="ignore")
        resp = Selector(text=body)

        if resp.xpath('//span[@class="st"]/text()'):
            for data in resp.xpath('//span[@class="st"]/text()').getall():
                if '@' in data:
                    for word in data.split():
                        if '@' in word:
                            if not re.search(r"[a-z0-9\.\-+_]+\@[a-z0-9\.\-+_]+\.[a-z]+", word):
                                email = word + domain
                            else:
                                email = word
                            (user, domain) = email.split('@')
                            if len(domain.split('.')) != 1 and not re.match(r'\d+', domain.split('.')[-1]):
                                if not email.startswith('@'):
                                    email = email.strip('-').strip('.')
                                    email = re.sub(r'\s+|\[|\]', '', email)
                                    email_addresses.append(email)
                    if not email_addresses:
                        print(
                            f'ERROR: Email not found in Google search - {response.url}')
        unique_emails = list(dict.fromkeys([x.lower() for x in email_addresses]))
        yield Request(
            f'http://domdetailer.com/api/checkDomain.php?domain={response.meta["domain"]}&app=DomDetailer&apikey={self.dom_detailer_api_key}&majesticChoice=root',
            headers=self.headers,
            callback=self.parse_dom_details,
            meta={
                'dont_proxy': True,
                'url': response.meta['url'],
                'domain': response.meta['domain'],
                'email': unique_emails[0] if unique_emails else 'NA',
            }
        )

    def parse_dom_details(self, response):
        if response.headers.get('Content-Type'):
            try: 
                json_data = json.loads(response.text)
            except:
                json_data = {}
        else:
            json_data = {}
    
        yield {
            'website': response.meta['domain'],
            'url': response.meta['url'],
            'email': response.meta['email'],
            'da': json_data['mozDA'] if json_data.get('mozDA') else 'NA',
            'pa': json_data['mozPA'] if json_data.get('mozPA') else 'NA',
            'cf': json_data['majesticCF'] if json_data.get('majesticCF') else 'NA',
            'tf': json_data['majesticTF'] if json_data.get('majesticTF') else 'NA'
        }

    # def _filter_emails(self, emails):
    #     for email in emails:
    #         # Check if '.png' not in email
    #         if email.endswith('.jpg'):
    #             continue
    #         # Check if '.jpg' not in email
    #         if email.endswith('.png'):
    #             continue
    #         # Check 'gif' not in email:
    #         if email.endswith('.gif'):
    #             continue
    #         (user, domain) = email.split('@')
    #         # Check if domain part of the extracted email is not like user@domain eg - a@b
    #         # Check if root domain of the email domain is not a number eg css@1.2.4
    #         if len(domain.split('.')) > 1 and not re.match(r'\d+', domain.split('.')[-1]):
    #             # Check the email string does not start with @ eg- @twitterhandle
    #             if not email.startswith('@'):
    #                 email = email.strip('-').strip('.')
    #                 email = re.sub(r'\s+|\[|\]', '', email)
    #                 self.email_addresses.append(email)

    def _filter_emails(self, email):
        # Check if '.png' not in email
        if email.endswith('.jpg'):
            pass
        # Check if '.jpg' not in email
        elif email.endswith('.png'):
            pass
        # Check 'gif' not in email:
        elif email.endswith('.gif'):
            pass
        else:
            (user, domain) = email.split('@')
            # Check if domain part of the extracted email is not like user@domain eg - a@b
            # Check if root domain of the email domain is not a number eg css@1.2.4
            if len(domain.split('.')) > 1 and not re.match(r'\d+', domain.split('.')[-1]):
                # Check the email string does not start with @ eg- @twitterhandle
                if not email.startswith('@'):
                    email = email.strip('-').strip('.')
                    email = re.sub(r'\s+|\[|\]', '', email)
                    self.email_addresses.append(email)
    
    def _read_pdf(self, response_body):
        body = ""
        # body = response.body.decode("utf-8", errors="ignore")
        with open('response.pdf', 'wb') as file:
            file.write(response_body)
        # creating a pdf file object
        pdfFileObj = open('response.pdf', 'rb')
        # creating a pdf reader object
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        # Go through all the pages and extract text
        for page_num in range(pdfReader.numPages):
            # creating a page object
            pageObj = pdfReader.getPage(page_num)
            # extracting text from page
            body += pageObj.extractText()
        return body