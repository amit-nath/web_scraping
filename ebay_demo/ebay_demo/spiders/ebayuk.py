# -*- coding: utf-8 -*-
import logging
import re
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http.request import Request


class EbayukSpider(CrawlSpider):
    name = 'ebayuk'
    allowed_domains = ['www.ebay.co.uk']
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'

    def start_requests(self):
        yield Request(
            'https://www.ebay.co.uk/',
            headers={'User-Agent': self.user_agent}
        )

    rules = (
        Rule(LinkExtractor(
            restrict_xpaths='//a[@class="hl-cat-nav__js-link"]'), follow=True, process_request='set_user_agent'),
        Rule(LinkExtractor(
            restrict_xpaths='//a[@class="b-tile"]'), callback='parse_item', process_request='set_user_agent'),
    )

    def set_user_agent(self, request):
        request.headers['User-Agent'] = self.user_agent
        return request

    def parse_item(self, response):
        item_image_url = response.xpath('//*[@id="icImg"]/@src').get()
        item_name = response.xpath('//h1[@id="itemTitle"]/text()').get()
        if response.xpath("//span[@id='prcIsum']"):
            item_price = response.xpath("//span[@id='prcIsum']/text()").get()
            # logging.info('Item price - ' + str(item_price))
            item_price = re.sub(r'£| each|,|EUR |US $', '', item_price)
            # item_price = item_price.replace('£', '').replace(' each', '').replace(r',','').strip()
            # logging.info('Item price - ' + str(item_price))
        else:
            logging.warn(
                f'Price not found for - {item_name} - {item_image_url}')
            item_price = 0

        # logging.info('Item price - ' + str(item_price))
        # logging.info(int(float(item_price)))
        if int(float(item_price)) > 20:
            yield {
                'name': item_name,
                'price': item_price,
                'url': response.url,
                'image_url': item_image_url,
            }
