# expedition2
PoC repo for expedition2


## How to get started

You should have Mongo installed and running. We will be using `test` database of Mongo for now.

Perform following steps to populate the DB (Tested with Python 2.7)

1. After cloning this repo - create a virtual environment using `virtualenv venv `

2. Then install all the required packages - `venv/bin/pip install -r requirements.txt`

3. Go to `exp2` directory and simply can try using `../venv/bin/scrapy crawl independent_tours` and `../venv/bin/scrapy crawl group_tours`.

