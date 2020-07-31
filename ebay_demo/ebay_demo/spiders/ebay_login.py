# -*- coding: utf-8 -*-
import logging
import requests
import scrapy

from scrapy.selector import Selector

from ebay_demo.config.credentials import EBAY_USERNAME, EBAY_PASSWORD


class EbayLoginSpider(scrapy.Spider):
    name = 'ebay_login'
    allowed_domains = ['www.ebay.com']
    start_urls = ['https://www.ebay.com/']

    def __init__(self, item_id):
        self.url = 'https://www.ebay.com/'
        self.login_status = False
        self.home_page = None
        self.login_payload = {}
        self.item_id = item_id

        self.session = requests.Session()
        self.session.headers = {
            'authority': 'www.ebay.com',
            'pragma': 'no-cache',
            'cache-control': 'no-cache',
            'upgrade-insecure-requests': '1',
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'en-US,en;q=0.9',
            'accept-encoding': 'gzip, deflate, br'
        }
        
        try:
            response = self.session.get(self.url, verify=False)
            if response.status_code == 200:
                print(f'[INFO]  Successfully accessed {self.url} page\n')
                self.login(response.content)
            else:
                print('[ERROR] Unexpected code %s received' %
                      response.status_code)
        except ConnectionError as e:
            print(e)
            print("[ERROR] Failed to connect to: " + self.url)
            exit(1)
    
    # @classmethod
    # def from_crawler(cls, crawler, *args, **kwargs):
    #     spider = super(EbayLoginSpider, cls).from_crawler(
    #         crawler, *args, **kwargs)
    #     crawler.signals.connect(spider.spider_closed,
    #                             signal=scrapy.signals.spider_closed)
    #     return spider

    # def spider_closed(self, spider):
    #     logging.info('Spider is closing. Logging out from Ebay ...')
    #     self.logout()

    def login(self, body):
        self._cookie = self._get_cookie()
        self._open_login_page(body)

        print("[INFO]  Login to: %s" % self.login_link)
        self.session.headers.update({'Referer': self.url})
        self.login_payload.update({
            'userid': EBAY_USERNAME,
            'pass': EBAY_PASSWORD,
            'isRecgUser': 'true' if self.login_payload['recgUser'] else 'false'
        })
        response = self.session.post(
            self.login_link, data=self.login_payload)
        if response.status_code == 200:
            print(f'[INFO]  Login to {self.url} - PASSED\n')
            self.login_status = True
            self.home_page = response.content
        else:
            print(f'[ERROR] Login to {self.url} - FAILED')
            print(
                f'        Unexpected code {response.status_code} received')
            exit(1)

    def logout(self):
        if self.login_status:
            resp = Selector(text=self.home_page)
            logout_link = resp.xpath('//a[contains(text(), "Sign out")]/@href').get()
            logging.debug(f'Sign-Out Link - {logout_link}')

            try:
                response = self.session.get(logout_link, verify=False)
                if response.status_code == 200:
                    print(f'[INFO]  Logout from {self.url} - PASSED\n')
                else:
                    logging.error(f'Logout from {self.url} - FAILED')
                    logging.error(f'Status code - {response.status_code}')
            except ConnectionError as e:
                print(e)
                print("[ERROR] Failed to connect to: " + logout_link)
                exit(1)
            finally:
                self.session.close()

    def _get_cookie(self):
        cookies = []
        for key, value in self.session.cookies.get_dict().items():
            cookies.append('%s=%s' % (key, value))
        cookie = "; ".join(cookies)
        print('[INFO]  Cookie: %s' % cookie)
        return cookie

    def _open_login_page(self, body):
        # print(body)
        resp = Selector(text=body)
        self.login_link = resp.xpath(
            '//a[contains(text(), "Sign in")]/@href').get()
        logging.debug(f'Sign-In Link - {self.login_link}')

        try:
            self.session.headers.update({'origin': self.url})
            response = self.session.get(self.login_link, verify=False)
            if response.status_code == 200:
                print(f'[INFO]  Successfully accessed {self.login_link} page\n')
                self._get_login_payload(response.text)
            else:
                print('[ERROR] Unexpected code %s received' %
                      response.status_code)
        except ConnectionError as e:
            print(e)
            print("[ERROR] Failed to connect to: " + self.login_link)
            exit(1)

    def _get_login_payload(self, body):
        # logging.debug(body)
        resp = Selector(text=body)
        # hidden_inputs = resp.xpath(".//div[@class='kmsi-container']/following-sibling::input[@type='hidden']").get()
        hidden_inputs = resp.xpath("//form[@id='signin-form']/child::input[@type='hidden']")
        logging.debug(hidden_inputs)
        for h_input in hidden_inputs:
            logging.debug(h_input)
            name = h_input.xpath(".//@name").get()
            value = h_input.xpath(".//@value").get()
            self.login_payload[name] = value
        logging.info(self.login_payload)

    def start_url_parse(self):
        pass

    def parse(self, response):
        if response.xpath("//*[@id='gh-uo']/a[contains(text(), 'Sign out')]"):
            logging.info('Ebay login successful')
        
        check_out_url = "https://pay.ebay.com/rxo"
        params = (
            ('action', 'create'),
            ('rypsvc', 'true'),
            ('pagename', 'ryp'),
            ('TransactionId', '-1'),
            ('item', f'{self.item_id}'),
            ('quantity', '1'),
        )
        # 'https://www.ebay.com/itm/153941928394'
        self.session.headers.update({'Referer': f'{self.url}/itm/{self.item_id}'})
        response = self.session.get(check_out_url, params=params, verify=False)
        logging.debug(response.content)
        resp = Selector(response.content)
        payment_url = resp.xpath("// form[@id='page-form']/@action").get()
        logging.info(f'Payment URL - {payment_url}')
        referer_url = payment_url.replace('cofirm', 'view')
        logging.info(f'Referer URL - {referer_url}')
        srt = resp.xpath("//form[@id='page-form']/input[@type='hidden']/@value").get()
        logging.info(f'SRT - {srt}')

        try:
            self.session.headers.update({'Referer': referer_url})
            response = self.session.get(payment_url, verify=False, data={'srt': srt})
            if response.status_code == 200:
                print(
                    f'[INFO]  Successfully placed order for {self.item_id}\n')
                self._get_login_payload(response.text)
            else:
                print('[ERROR] Unexpected code %s received' %
                      response.status_code)
        except ConnectionError as e:
            print(e)
            print("[ERROR] Failed to connect to: " + self.login_link)
            exit(1)


